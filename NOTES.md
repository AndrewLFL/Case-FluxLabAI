# Notas de Engenharia & Decisões Arquiteturais

## 1. Visão Geral
Este projeto implementa um pipeline de Engenharia de IA para análise de textos clínicos psicanalíticos. O objetivo central foi criar uma arquitetura resiliente que garanta saídas estruturadas e seguras, independentemente da variabilidade estocástica dos LLMs.

A solução foi construída sobre três pilares:
1.  **Orquestração de Estado:** LangGraph.
2.  **Validação Rigorosa:** Pydantic (Schema & Custom Validators).
3.  **Resiliência de API:** Implementação de padrão Fallback (Try/Catch).

---

## 2. Gestão de Dependências: Padrão Fallback (Híbrido)

Durante o desenvolvimento, foi identificado que a chave de API fornecida retornava erros de `429 - Billing Not Active` (falta de saldo na conta OpenAI).

### A Solução: Arquitetura Resiliente
Em vez de "chumbar" (hardcode) um Mock ou travar o sistema com o erro, implementei uma lógica de **Fallback Automático** na função `call_model`:

1.  **Tentativa Primária:** O sistema tenta conectar à API da OpenAI (`gpt-4o-mini`).
2.  **Captura de Erro:** Se houver exceção (Erro de Conexão, Billing, Rate Limit), o sistema captura o erro silenciosamente no log.
3.  **Ativação do Mock:** O sistema comuta automaticamente para um **Mock (Simulação)** que retorna um JSON estruturado válido.

**Por que isso é importante?**
Essa abordagem simula um ambiente de produção real (padrão *Circuit Breaker*). Garante que o pipeline de validação (downstream) possa ser testado e demonstrado mesmo quando o serviço externo (upstream) está indisponível.

---

## 3. Engenharia de Prompt (v1 vs. v2)

A evolução dos prompts foi focada em **Controlabilidade**:

* **Prompt v1 (Raw):** Focado apenas na instrução semântica ("Analise o caso").
    * *Problema:* O modelo retornava texto livre ou Markdown, quebrando o parser JSON.
* **Prompt v2 (Structured):**
    * **System Role:** Define a persona ("IA Clínica").
    * **JSON Enforcement:** Instrução explícita e reiterada para saída JSON.
    * **Constraint Injection:** As regras de negócio (ex: "lista entre 3 e 6 itens") foram injetadas no texto do prompt. Isso aumenta o acerto "Zero-shot", reduzindo a carga de rejeição do validador.

---

## 4. Validação e Regras de Negócio (Pydantic)

A validação foi a etapa mais crítica para garantir a segurança clínica dos dados.

### 4.1. Validação de Tamanho da Análise (Custom Validator)
O requisito exigia que a análise tivesse "entre 4 e 8 linhas". Como "linhas" é uma medida visual subjetiva, converti essa regra para uma métrica determinística: **Contagem de Palavras**.

Implementei um `@field_validator` na classe `ClinicalOutput`:
* **Lógica:** Rejeita textos com < 40 palavras (muito rasos) ou > 200 palavras (prolixos).
* **Resultado:** Garante a concisão exigida sem depender de quebras de linha (`\n`) instáveis do modelo.

### 4.2. Estrutura e Vocabulário
* **Listas:** Uso de `min_length` e `max_length` para temas, significantes e perguntas.
* **Risco (Enums):** Uso de `Literal["baixo", "médio", "alto"]` para impedir alucinação de novos níveis de risco não protocolados.

---

## 5. Orquestração (LangGraph)

Optei pelo LangGraph (`StateGraph`) para desacoplar a geração da validação.
* **Generation Node:** Responsável apenas pelo I/O com o modelo (ou Mock).
* **Validation Node:** Atua como *Guardrail*. Se o JSON vier quebrado ou fugir das regras, o erro é catalogado no estado (`errors`) sem interromper o processamento em lote dos outros arquivos.

---

## 6. Conclusão

O sistema entregue demonstra maturidade de engenharia ao priorizar a continuidade do serviço. Mesmo diante de falhas na API externa, o pipeline mantém sua integridade funcional, validando dados e gerando relatórios estruturados prontos para integração em sistemas de prontuário eletrônico.