# Pipeline de IA Clínica (Psicanálise)

Este projeto implementa um pipeline de Engenharia de IA para processamento de textos clínicos. O sistema utiliza **LangGraph** para orquestração de fluxo e **Pydantic** para validação rigorosa de dados (Structured Output), garantindo que a saída do modelo atenda a regras de negócio clínicas.

## 🔑 Configuração da API (OpenAI)

Para que o pipeline utilize o modelo real (GPT-4o-mini), é necessário configurar uma chave de API da OpenAI.

1. Crie um arquivo chamado `.env` na raiz do projeto (mesma pasta do `pipeline.py`).
2. Adicione sua chave de API neste arquivo seguindo o formato abaixo:

```env
OPENAI_API_KEY=sk-proj-sua-chave-aqui...
```
## 📋 Funcionalidades

* **Ingestão de Dados:** Leitura de múltiplos arquivos clínicos (`.txt`).
* **Orquestração (LangGraph):** Fluxo controlado entre nós de geração e validação.
* **Validação de Schema (Pydantic):**
    * Verificação de tipos (Strict Typing).
    * Restrições de tamanho (ex: `themes` entre 3-6 itens).
    * Vocabulário controlado para avaliação de risco (`Literal['baixo', 'médio', 'alto']`).
* **Prompt Engineering:** Suporte a versionamento de prompts (v1 Raw vs v2 Structured).

## 🛠️ Instalação

1. Clone o repositório e instale as dependências:
   ```bash
   pip install openai langgraph pydantic python-dotenv
