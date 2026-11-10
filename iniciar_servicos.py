"""Sobe os três microsserviços de uma vez (cada um em seu próprio processo).

Uso:  python iniciar_servicos.py
Para encerrar: Ctrl+C
"""
import subprocess
import sys
import time

SERVICOS = [
    ("catalogo.app:app", 8001, "Catálogo"),
    ("pagamentos.app:app", 8003, "Pagamentos"),
    ("usuarios.app:app", 8004, "Usuários"),
    ("pedidos.app:app", 8002, "Pedidos"),
    ("gateway.app:app", 8000, "API Gateway"),
]


def main():
    processos = []
    try:
        for modulo, porta, nome in SERVICOS:
            p = subprocess.Popen([
                sys.executable, "-m", "uvicorn", modulo,
                "--host", "127.0.0.1", "--port", str(porta), "--log-level", "warning",
            ])
            processos.append(p)
            print(f"[ok] Serviço de {nome} em http://127.0.0.1:{porta}")
        print("\nTodos os serviços no ar.")
        print("Abra a loja no navegador: http://127.0.0.1:8000")
        print("Pressione Ctrl+C para encerrar.\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando serviços...")
    finally:
        for p in processos:
            p.terminate()


if __name__ == "__main__":
    main()
