# Projeto BI — Resultados Comerciais 2026

Painel Streamlit conectado diretamente à planilha compartilhada no Google Sheets.
Os dados são atualizados sob demanda pelo botão **Atualizar Dados**.
Os painéis usam a identidade visual de Paulo Lopes Advogados; mantenha
`logo-paulo-lopes.jpg` no projeto para que o Streamlit e a exportação HTML exibam
a marca.

## Preparação

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

O painel será aberto em `http://localhost:8501`.

## Acesso à planilha

O app lê a aba `RESULTADO` e as abas mensais da planilha. Para que o Streamlit
Cloud possa acessá-la sem credenciais, configure o compartilhamento como
**qualquer pessoa com o link pode visualizar**. O cache dura até cinco minutos;
o botão **Atualizar Dados** limpa o cache e busca os dados novamente.

## Publicação no Streamlit Cloud

Publique o repositório no GitHub e configure o arquivo principal como
`projeto-bi/app.py` (ou `app.py` se o repositório tiver como raiz esta pasta).
O `requirements.txt` desta pasta será usado para instalar as dependências.

## Exportar painel estático para compartilhamento

```powershell
python build_dashboard_html.py
```

O comando gera `dashboard-diretoria.html` a partir dos CSVs em `data/`, que podem
ser criados localmente pelo script `generate_data.py` usando `contratos-fechados.xlsx`.
Esses arquivos são ignorados pelo Git para evitar publicar dados locais de clientes.
