r"""
Cliente MCP + LLM LOCAL con Ollama: un modelo de codigo abierto decide que herramientas usar.

Es la version "sin API de pago" de cliente_llm.py: el modelo se ejecuta en tu equipo
(o en un servidor) a traves de Ollama.

Uso:
    python cliente_ollama.py                                   # servidor de ejemplo
    python cliente_ollama.py --modelo qwen2.5:7b               # otro modelo
    python cliente_ollama.py --cwd RUTA\mcp-renfe -- RUTA\mcp-renfe\.venv\Scripts\python.exe server_gtfs.py
    python cliente_ollama.py --modelo {modelo usado} --max-chars 0 --cwd {ruta a la carpeta desde la que se lanza el servidor MCP} -- {ruta al script del ejecutable de python en el entorno del servidor} {ruta al fichero del servidor}

IMPORTANTE: el modelo debe admitir herramientas (function calling), se puede comprobar en
https://ollama.com/library que el modelo concreto tiene la etiqueta "tools".
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ollama import AsyncClient, ResponseError

MAX_RONDAS = 8   # limite de llamadas a herramientas por pregunta


def system_prompt() -> str:
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        "Eres un asistente que responde usando UNICAMENTE las herramientas disponibles. "
        "No inventes datos: si necesitas informacion, llama a una herramienta. "
        "Si falta algun dato necesario (ciudad, hora, fecha...), preguntalo. "
        "Responde en espanol, de forma breve. "
        f"La fecha y hora local actuales son {ahora} (usalas para 'hoy', 'manana' o 'ahora')."
    )


def herramientas_para_ollama(tools) -> list[dict]:
    """Convierte las tools del servidor MCP al formato de function calling de Ollama."""
    return [{"type": "function",
             "function": {"name": t.name, "description": t.description or "",
                          "parameters": t.inputSchema}} for t in tools]


async def responder(client, session, tools, mensajes: list, modelo: str, verbose: bool = True, ctx: int = 8192, max_chars: int = 200) -> str:
    """Procesa una pregunta (ya anadida a `mensajes`) hasta obtener la respuesta final."""
    for _ in range(MAX_RONDAS):
        resp = await client.chat(model=modelo, messages=[{"role": "system", "content": system_prompt()}] + mensajes,
                                 tools=tools, options={"num_ctx": ctx})
        msg = resp.message
        mensajes.append(msg)

        if not msg.tool_calls:
            return msg.content or ""

        for tc in msg.tool_calls:
            nombre, args = tc.function.name, dict(tc.function.arguments)
            if verbose:
                print(f"  [tool] {nombre}({json.dumps(args, ensure_ascii=False)})")
            res = await session.call_tool(nombre, args)
            texto = "\n".join(c.text for c in res.content if c.type == "text")
            if res.isError:
                texto = "ERROR: " + texto
            if verbose:
                if max_chars > 0 and len(texto) > max_chars:
                    print(f"  [resultado] {texto[:max_chars].replace(chr(10), ' ')}...")
                elif max_chars > 0:
                    print(f"  [resultado] {texto.replace(chr(10), ' ')}")
                else:                                  # max_chars = 0 -> mostrar todo
                    print("  [resultado]\n" + texto)
            mensajes.append({"role": "tool", "tool_name": nombre, "content": texto})
    return "(He alcanzado el limite de llamadas a herramientas sin llegar a una respuesta.)"


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modelo", default=os.getenv("OLLAMA_MODEL", "llama3.1:8b"))
    ap.add_argument("--max-chars", type=int, default=200, help="caracteres del resultado de cada tool que se muestran en pantalla (0 = todo)")
    ap.add_argument("--ctx", type=int, default=8192, help="tamano del contexto del modelo en tokens (por defecto 8192)")
    ap.add_argument("--host", default=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    ap.add_argument("--cwd", default=None, help="carpeta desde la que se lanza el servidor MCP (util si lee ficheros con rutas relativas)")
    ap.add_argument("servidor", nargs="*", help="comando que arranca el servidor MCP (por defecto, el de ejemplo)")
    a = ap.parse_args()

    cmd = a.servidor or [sys.executable, "servidor_trafico.py"]
    params = StdioServerParameters(command=cmd[0], args=cmd[1:], cwd=a.cwd)
    client = AsyncClient(host=a.host)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = herramientas_para_ollama((await session.list_tools()).tools)
            print(f"Modelo: {a.modelo} | Ollama: {a.host}")
            print("Herramientas:", ", ".join(t["function"]["name"] for t in tools))
            print("Escribe tu pregunta (o 'salir').\n")

            mensajes: list = []
            while True:
                pregunta = (await asyncio.to_thread(input, "Tú: ")).strip()
                if pregunta.lower() in ("salir", "exit", "q"):
                    break
                if not pregunta:
                    continue
                mensajes.append({"role": "user", "content": pregunta})
                try:
                    print("Asistente:", await responder(client, session, tools, mensajes, a.modelo, ctx=a.ctx, max_chars=a.max_chars), "\n")
                except ResponseError as e:
                    print(f"Error de Ollama: {e}\n"
                          "Comprueba que Ollama esta en marcha, que has descargado el modelo "
                          f"(ollama pull {a.modelo}) y que ese modelo admite herramientas.\n")
                    mensajes.pop()
                except Exception as e:
                    print(f"No se pudo conectar con Ollama ({a.host}): {e}\n")
                    mensajes.pop()


if __name__ == "__main__":
    asyncio.run(main())