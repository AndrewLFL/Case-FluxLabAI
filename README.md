# Pipeline de IA Clínica (Psicanálise)

Este projeto implementa um pipeline de Engenharia de IA para processamento de textos clínicos. O sistema utiliza **LangGraph** para orquestração de fluxo e **Pydantic** para validação rigorosa de dados (Structured Output), garantindo que a saída do modelo atenda a regras de negócio clínicas.

## ⚠️ Nota Importante sobre a Execução

**Status Atual: MOCK MODE ATIVO**

Durante o desenvolvimento, a chave de API fornecida retornou erro `429 - Billing Not Active` (conta sem saldo). Para garantir a avaliação da arquitetura de engenharia (validações, fluxo de grafo e estruturação de dados), o sistema foi configurado para usar um **Mock (Simulação)** no nó de geração.

Isso permite testar todo o pipeline (Leitura -> Geração Simulada -> Validação Pydantic -> Relatório) sem dependência da API externa.

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