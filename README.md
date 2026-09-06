# Artes da Roosenvelt Robotic B2C

Este repositório serve as artes dos carrosséis do [@agendab2c](https://instagram.com/agendab2c)
e publica uma peça a cada três dias.

Ele é **público por necessidade técnica**: a API de publicação do Instagram não
aceita upload de arquivo, só URL pública — e URL bruta de repositório privado
exige token, que a Meta não envia. As imagens vão ao ar no Instagram de
qualquer forma, então não há nada a proteger aqui.

## Como funciona

```
artes/<peça>/01.png … 06.png    os slides
fila.json                       o que publicar, quando, e com que legenda
publicar_instagram.py           faz as 3 chamadas da API da Meta
.github/workflows/publicar.yml  roda todo dia às 9h de Brasília
```

Todo dia a Action lê a `fila.json`. Se houver peça vencida e não publicada, ela
publica **uma** — mesmo que haja atraso acumulado, para não encher o feed de
quem segue. Depois marca como publicada e faz commit, então o histórico deste
repositório é o registro do que foi ao ar.

## Segredos necessários

Em *Settings → Secrets and variables → Actions*:

| Segredo | O que é |
|---|---|
| `IG_USER_ID` | id numérico da conta Instagram Business |
| `META_TOKEN` | token com a permissão `instagram_content_publish` |

Sem os dois, a Action falha de propósito, em vez de fingir que publicou.

## Publicar fora de hora

*Actions → Publicar no Instagram → Run workflow*. Ele publica a próxima peça
vencida, se houver.

## De onde vêm as artes

Do gerador em `roosenvelt-conteudo/`, que monta os slides a partir de arquivos
de texto. Para preparar uma leva nova:

```bash
python publicador.py --preparar --usuario UryelNiiChan --repositorio roosenvelt-artes
```
