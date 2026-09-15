"""Publica no Instagram a proxima peca vencida da fila.

Roda sozinho pelo GitHub Actions, uma vez por dia. Se nao houver peca vencida,
sai sem fazer nada - por isso pode rodar todo dia sem risco.

Precisa de dois segredos no repositorio:
    IG_USER_ID       id da conta Instagram Business (numero)
    META_TOKEN       token com instagram_content_publish

Publicar carrossel na Meta sao tres etapas: cada imagem vira um "container",
os containers viram um container de carrossel, e so entao publica. A API nao
aceita upload de arquivo - so URL publica, que e o que este repositorio serve.
"""

import json
import os
import sys
import time
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

VERSAO = "v25.0"
BASE = f"https://graph.facebook.com/{VERSAO}"
FILA = Path(__file__).parent / "fila.json"

# Entre criar o container e publicar, a Meta precisa buscar a imagem na URL.
# Publicar cedo demais devolve "media not ready" - por isso consulta o status.
LIMITE_ESPERA = 120      # segundos, por container


def _post(caminho: str, dados: dict) -> dict:
    corpo = urlencode(dados).encode()
    req = Request(f"{BASE}/{caminho}", data=corpo, method="POST")
    try:
        with urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except HTTPError as erro:
        # sem isso o log mostra so "HTTP 400", sem dizer o que a Meta recusou
        raise RuntimeError(f"Meta recusou {caminho}: {erro.read().decode()}") from None


def _esperar_pronto(container: str, token: str) -> None:
    """Aguarda o container sair de IN_PROGRESS. ERROR ou EXPIRED param tudo."""
    inicio = time.time()
    while True:
        url = f"{BASE}/{container}?fields=status_code,status&access_token={token}"
        with urlopen(url, timeout=30) as r:
            dados = json.loads(r.read())
        estado = dados.get("status_code")
        if estado == "FINISHED":
            return
        if estado in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {container} falhou: {dados.get('status')}")
        if time.time() - inicio > LIMITE_ESPERA:
            raise RuntimeError(f"container {container} nao ficou pronto em {LIMITE_ESPERA}s")
        time.sleep(3)


def publicar(item: dict, ig_user: str, token: str, teste: bool = False) -> str | None:
    imagens = item["imagens"]
    if not 2 <= len(imagens) <= 10:
        raise RuntimeError(f"carrossel aceita de 2 a 10 imagens, veio {len(imagens)}")

    print(f"  {item['peca']}: {len(imagens)} imagens")

    # 1. um container por imagem
    filhos = []
    for i, url in enumerate(imagens, 1):
        r = _post(f"{ig_user}/media", {
            "image_url": url,
            "is_carousel_item": "true",
            "access_token": token,
        })
        filhos.append(r["id"])
        print(f"    {i}/{len(imagens)} container {r['id']}")

    for filho in filhos:
        _esperar_pronto(filho, token)
    print("    imagens processadas pela Meta")

    # 2. o container do carrossel, com a legenda
    pai = _post(f"{ig_user}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(filhos),
        "caption": item.get("legenda", ""),
        "access_token": token,
    })["id"]
    print(f"    carrossel {pai}")

    _esperar_pronto(pai, token)

    if teste:
        # Tudo que pode dar errado ja aconteceu ate aqui: token, permissao,
        # URL da imagem, formato, legenda. Container nao publicado expira
        # sozinho em 24h e ninguem ve.
        print("    TESTE: carrossel pronto para publicar - parando antes de publicar")
        return None

    # 3. publica
    publicado = _post(f"{ig_user}/media_publish", {
        "creation_id": pai,
        "access_token": token,
    })["id"]
    print(f"    publicado: {publicado}")
    return publicado


def main() -> None:
    ig_user = os.environ.get("IG_USER_ID", "").strip()
    token = os.environ.get("META_TOKEN", "").strip()
    if not ig_user or not token:
        print("  faltam os segredos IG_USER_ID e META_TOKEN")
        sys.exit(1)

    dados = json.loads(FILA.read_text(encoding="utf-8"))
    hoje = date.today().isoformat()
    teste = os.environ.get("MODO", "publicar") == "teste"

    pendentes = [i for i in dados["fila"] if not i["publicado"]]
    vencidas = [i for i in pendentes if i["quando"] <= hoje]
    if teste:
        # no teste vale a proxima da fila, vencida ou nao
        vencidas = pendentes[:1]
        print("  MODO TESTE: nada sera publicado")
    if not vencidas:
        print("  nada vencido hoje")
        return

    # uma por execucao, mesmo que haja atraso acumulado: publicar tres de uma
    # vez enche o feed do seguidor e parece spam
    item = vencidas[0]
    if len(vencidas) > 1:
        print(f"  {len(vencidas)} vencidas; publicando so a primeira")

    id_post = publicar(item, ig_user, token, teste)
    if teste:
        print(f"{chr(10)}  teste concluido: token, permissoes e artes funcionando")
        return
    item["publicado"] = True
    item["publicado_em"] = hoje
    item["id_post"] = id_post

    FILA.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{chr(10)}  fila atualizada")


if __name__ == "__main__":
    main()
