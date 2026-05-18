import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date
from firecrawl import FirecrawlApp
import anthropic

# --- Configuração ---
FIRECRAWL_API_KEY = os.environ["FIRECRAWL_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GMAIL_SENDER     = os.environ["GMAIL_SENDER_EMAIL"]
GMAIL_PASSWORD   = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT_EMAIL  = GMAIL_SENDER  # envia para si mesmo; troque se quiser outro destinatário

TEMAS = ["tecnologia e inteligência artificial", "negócios e mercado financeiro", "política e atualidades"]

FONTES = [
    "https://news.google.com/rss/search?q=tecnologia+IA&hl=pt-BR&gl=BR&ceid=BR:pt-419",
    "https://news.google.com/rss/search?q=mercado+financeiro+economia&hl=pt-BR&gl=BR&ceid=BR:pt-419",
    "https://news.google.com/rss/search?q=politica+brasil+atualidades&hl=pt-BR&gl=BR&ceid=BR:pt-419",
    "https://techcrunch.com/feed/",
    "https://feeds.feedburner.com/venturebeat/SZYF",
]

# --- Coleta de notícias via Firecrawl ---
def coletar_noticias():
    app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
    conteudo_bruto = []

    for url in FONTES:
        try:
            result = app.scrape_url(url, params={"formats": ["markdown"]})
            texto = result.get("markdown", "")
            if texto:
                conteudo_bruto.append(f"=== FONTE: {url} ===\n{texto[:3000]}")
        except Exception as e:
            print(f"Erro ao raspar {url}: {e}")

    return "\n\n".join(conteudo_bruto)


# --- Geração do digest com Claude ---
def gerar_digest(conteudo_bruto):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    hoje = date.today().strftime("%d/%m/%Y")

    prompt = f"""Você é um curador de notícias. Abaixo estão conteúdos coletados de feeds de notícias hoje ({hoje}).

Sua tarefa:
1. Selecione entre 5 e 8 notícias relevantes sobre estes temas: {", ".join(TEMAS)}.
2. Para cada notícia, escreva um parágrafo curto (3 a 5 linhas) explicando o que aconteceu e por que importa.
3. Ordene por relevância e impacto.
4. Escreva em português brasileiro, tom profissional mas acessível.
5. Retorne APENAS o HTML do corpo do email, sem ```html``` ou explicações extras.

Formato de cada notícia no HTML:
<div class="noticia">
  <h3>Título da notícia</h3>
  <p class="tema">🏷 Tema</p>
  <p>Parágrafo explicativo aqui.</p>
</div>

Conteúdo coletado:
{conteudo_bruto[:12000]}
"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


# --- Montagem do email HTML ---
def montar_email(digest_html):
    hoje = date.today().strftime("%d de %B de %Y")
    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Georgia, serif; background: #f5f5f0; margin: 0; padding: 0; }}
  .container {{ max-width: 640px; margin: 32px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
  .header {{ background: #1a1a2e; color: #ffffff; padding: 28px 32px; }}
  .header h1 {{ margin: 0; font-size: 22px; letter-spacing: 0.5px; }}
  .header p {{ margin: 6px 0 0; font-size: 13px; color: #aaaacc; }}
  .body {{ padding: 24px 32px; }}
  .noticia {{ border-bottom: 1px solid #eeeeee; padding: 20px 0; }}
  .noticia:last-child {{ border-bottom: none; }}
  .noticia h3 {{ margin: 0 0 6px; font-size: 17px; color: #1a1a2e; line-height: 1.4; }}
  .noticia .tema {{ margin: 0 0 10px; font-size: 12px; color: #888888; font-family: sans-serif; }}
  .noticia p {{ margin: 0; font-size: 15px; color: #333333; line-height: 1.7; }}
  .footer {{ background: #f0f0eb; padding: 16px 32px; font-size: 12px; color: #999999; font-family: sans-serif; text-align: center; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Daily News Digest</h1>
    <p>{hoje} · Tecnologia · Negócios · Política</p>
  </div>
  <div class="body">
    {digest_html}
  </div>
  <div class="footer">
    Gerado automaticamente com Firecrawl + Claude · Enviado às 7h
  </div>
</div>
</body>
</html>
"""


# --- Envio do email ---
def enviar_email(html):
    hoje = date.today().strftime("%d/%m/%Y")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📰 Daily News Digest — {hoje}"
    msg["From"]    = GMAIL_SENDER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_SENDER, GMAIL_PASSWORD)
        smtp.sendmail(GMAIL_SENDER, RECIPIENT_EMAIL, msg.as_string())
    print(f"Email enviado para {RECIPIENT_EMAIL}")


# --- Main ---
if __name__ == "__main__":
    print("Coletando notícias...")
    conteudo = coletar_noticias()

    print("Gerando digest com Claude...")
    digest = gerar_digest(conteudo)

    print("Montando e enviando email...")
    html = montar_email(digest)
    enviar_email(html)
    print("Concluído!")
