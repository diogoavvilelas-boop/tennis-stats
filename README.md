# Tennis Stat Site

Gera automaticamente, todos os dias, uma pagina de estatisticas ("stat battle")
para cada jogo ATP e WTA do dia -- ultimos 10 jogos de cada jogador e registo
por tipo de piso (duro / terra batida / relva).

Como funciona: o GitHub Actions corre `scripts/build_site.py` todos os dias
de manha, o script vai buscar os jogos do dia + historico dos jogadores a
API Tennis, gera ficheiros HTML dentro de `docs/`, e o GitHub Pages publica
esse conteudo automaticamente.

## Configuracao (uma vez so)

1. **Cria uma conta gratuita em https://api-tennis.com** e copia a tua
   `APIkey` (Login > Dashboard).

2. **Cria um repositorio novo no GitHub** e faz upload de todos estes
   ficheiros (ou usa `git push`).

3. **Adiciona a chave da API como secret do repositorio**:
   `Settings -> Secrets and variables -> Actions -> New repository secret`
   - Nome: `API_TENNIS_KEY`
   - Valor: a tua APIkey da api-tennis.com

4. **Ativa o GitHub Pages**:
   `Settings -> Pages -> Source: Deploy from a branch -> Branch: main, pasta: /docs`

5. **Corre o workflow uma vez manualmente** para gerar o primeiro conteudo:
   separador `Actions -> Build daily tennis stat site -> Run workflow`.

Depois disto, o site atualiza-se sozinho todos os dias as 06:00 UTC (podes
mudar a hora no ficheiro `.github/workflows/daily-build.yml`, campo `cron`).
O site fica disponivel em `https://<o-teu-utilizador>.github.io/<repo>/`.

## Testar localmente

```bash
cd scripts
APIKEY=a_tua_chave python3 build_site.py
```

Isto cria a pasta `docs/` com `index.html` (lista de jogos de hoje) e
`docs/matches/<id>.html` (uma pagina por jogo).

## Limitacoes a saber

- O plano gratuito da API Tennis tem um limite de pedidos -- se tiveres
  muitos jogos num dia (ex.: 40+ em simultaneo nos dois circuitos), pode ser
  necessario um plano pago para nao esgotares a quota.
- Os tipos de evento `265` (ATP Singles) e `266` (WTA Singles) foram
  confirmados na documentacao da API em 2026; se a API os mudar, atualiza a
  dicionario `EVENT_TYPES` em `scripts/build_site.py`.
- O registo por piso vem das estatisticas agregadas da epoca (nao um calculo
  jogo-a-jogo dos ultimos 10), porque a API nao devolve o piso de cada jogo
  individual no historico H2H.
- O design é propositadamente simples (HTML + CSS puro, sem frameworks) para
  ser facil de editar. Podes mudar cores e layout em `scripts/build_site.py`
  (variavel `STYLE_CSS`) ou pedir-me para redesenhar.
