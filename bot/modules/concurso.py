import asyncio
import re
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from google.genai import types

from config import logger
from services.gemini_service import GeminiService
from services.conversation_service import conversation_service
from services.mcp_client import pci_mcp_client
from services.output_handler import output_handler

_gemini = GeminiService()

async def concurso_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /concurso.
    Também pode ser chamado caso a mensagem contenha @concurso.
    """
    chat_id = update.effective_chat.id
    message = update.message
    
    texto_input = ""
    if message.text:
        texto_input = message.text
        # Se for o comando, remove "/concurso"
        if texto_input.startswith("/concurso"):
            texto_input = texto_input.replace("/concurso", "", 1).strip()
    
    if not texto_input:
        texto_input = "Quais são os concursos abertos no momento?"
    
    requires_audio_reply = bool(re.search(r"(responda|fale|diga) (em|por) (áudio|voz)", texto_input.lower()))
    
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    
    try:
        # Inicializa o MCP do PCI Concursos
        instrucoes_mcp = await pci_mcp_client.initialize()
        tools_mcp = await pci_mcp_client.list_tools()
        
        # Mapeia as ferramentas para o formato Gemini
        gemini_tools = []
        function_declarations = []
        for t in tools_mcp:
            # Converte JSON schema paramters format
            params = t.get("inputSchema", {})
            if "type" not in params:
                params["type"] = "OBJECT"
            
            # Precisamos adequar o schema ao formato esperado pela google-genai
            decl = types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=params
            )
            function_declarations.append(decl)
            
        if function_declarations:
            gemini_tools.append(types.Tool(function_declarations=function_declarations))
            
        # Recupera histórico e salva a mensagem atual
        historico = conversation_service.get_history(chat_id)
        conversation_service.add_message(chat_id, "user", texto_input)
        
        # Monta o system_instruction combinando as instruções do MCP
        sys_inst = (
            "Você é um assistente especializado em Concursos Públicos.\n"
            f"{instrucoes_mcp}\n\n"
            "Responda de forma clara, amigável e resumida. Utilize as ferramentas disponíveis para buscar informações.\n"
            "Formate a resposta em Markdown limpo."
        )
        
        # Prepara a chamada para o Gemini
        contents = []
        for turno in historico[-4:]:
            role = "user" if turno["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=turno["content"])]))
        
        if contents and contents[0].role == "model":
            contents = contents[1:]
            
        contents.append(types.Content(role="user", parts=[types.Part(text=texto_input)]))
        
        # Loop ReAct manual para lidar com chamadas de ferramenta
        max_steps = 5
        current_step = 0
        texto_final = []
        
        modelo = GeminiService.MODELO_CHAT
        
        while current_step < max_steps:
            current_step += 1
            
            config = types.GenerateContentConfig(
                system_instruction=sys_inst,
                tools=gemini_tools if gemini_tools else None,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
            
            res = await _gemini.client.aio.models.generate_content(
                model=modelo,
                contents=contents,
                config=config
            )
            
            if not res or not res.candidates:
                break
                
            candidate = res.candidates[0]
            parts = candidate.content.parts
            contents.append(candidate.content)
            
            texto_deste_passo = ""
            function_calls = []
            
            for part in parts:
                if part.text:
                    texto_parte = re.sub(r"<thought>.*?</thought>", "", part.text, flags=re.DOTALL).strip()
                    if texto_parte:
                        texto_deste_passo += texto_parte
                if part.function_call:
                    function_calls.append(part.function_call)
                    
            if texto_deste_passo and not function_calls:
                texto_final.append(texto_deste_passo)
                
            if not function_calls:
                break
                
            # Executar ferramentas
            tool_parts = []
            for fc in function_calls:
                logger.info(f"Executando MCP Tool: {fc.name}({fc.args})")
                # Converter Args se não for dict (Pode ser Struct)
                args_dict = dict(fc.args) if fc.args else {}
                try:
                    resultado = await pci_mcp_client.call_tool(fc.name, args_dict)
                except Exception as e:
                    resultado = f"Erro ao chamar ferramenta: {e}"
                    
                tool_parts.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"result": resultado}
                    )
                ))
            contents.append(types.Content(role="user", parts=tool_parts))
            
        resposta = "\n\n".join(texto_final).strip()
        if not resposta:
            resposta = "Não consegui encontrar as informações solicitadas."
            
        conversation_service.add_message(chat_id, "assistant", resposta)
        await output_handler.send_output(update, context, resposta, requires_audio=requires_audio_reply)
        
    except Exception as e:
        logger.error(f"Erro no módulo de concurso: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Falha ao buscar concursos: {e}")
