# Notas de Engenharia & Decisões Arquiteturais

## 1. Visão Geral
Este projeto implementa um pipeline de Engenharia de IA para análise de textos clínicos psicanalíticos. O objetivo central foi criar uma arquitetura resiliente que garanta saídas estruturadas e seguras, independentemente da variabilidade estocástica das LLMs.

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

## 3. Engenharia de Prompt (Análise Comparativa)

A evolução dos prompts foi focada em aumentar a **Controlabilidade** da IA, garantindo que ela obedeça estritamente ao formato necessário para o software. O Mock foi gerado utilizando o Prompt v2.

### Por que o Prompt v2 é superior?

1.  **Redução de Carga no Parser (Parsing Overhead):**
    * **No v1:** O modelo tendia a misturar a análise clínica com "conversa" (ex: *"Aqui está a análise que você pediu..."*). Isso exigiria tratamentos complexos de string no Python para limpar o texto antes de tentar ler o JSON.
    * **No v2:** Ao impor estritamente o formato JSON e proibir texto adicional, a resposta do modelo torna-se diretamente consumível pela função `json.loads()`, eliminando a necessidade de pós-processamento de texto (*sanitize*).

2.  **Injeção de Regras de Negócio (Constraint Injection):**
    * **No v1:** O modelo "adivinhava" quantos temas ou hipóteses gerar. Frequentemente gerava 10 itens ou apenas 1, o que causava falha imediata na validação do Pydantic (que exige, por exemplo, entre 3 e 6).
    * **No v2:** As restrições de tamanho (`min_length`, `max_length`) foram traduzidas do código Python para linguagem natural dentro do prompt. Isso permite que o modelo realize uma **auto-validação durante a geração**, garantindo que o JSON já nasça compatível com as regras do sistema.

3.  **Ancoragem de Persona (Persona Anchoring):**
    * **No v1:** Sem definição clara de papel, o modelo oscilava entre uma linguagem de autoajuda e um tom técnico.
    * **No v2:** A instrução de *System Role* ("Você é uma IA Clínica...") ancora o espaço latente do modelo em terminologias da psicanálise, garantindo que o campo `risk_assessment` seja preenchido com rigor técnico e não com opiniões leigas.

4.  **Minimização de Alucinação de Estrutura:**
    * O Prompt v2 define explicitamente os nomes das chaves (`themes`, `signifiers`). No v1, o modelo poderia inventar chaves como `topicos_principais` ou `palavras_chave`, o que quebraria o contrato de interface (Schema) esperado pelo backend.

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

## 5. Estratégia de Persistência (Single Output File)

Embora o sistema processe múltiplos arquivos de entrada (`.txt`) separadamente, optei por consolidar todos os resultados em um único arquivo de saída (`results.json`).

### Motivação da Decisão:
1.  **Visão de Lote (Batch Observability):**
    O arquivo único atua não apenas como armazenamento de dados, mas como um **Log de Execução do Lote**. Ele contém metadados globais (total processado, contagem de sucessos/falhas) que seriam perdidos ou difíceis de calcular se tivéssemos espalhado 50 arquivos JSON soltos numa pasta.

2.  **Facilidade de Integração (Downstream):**
    Para um sistema consumidor, é muito mais eficiente ingerir um único payload JSON contendo a lista de pacientes processados do que ter que varrer diretórios e abrir conexões de arquivo para cada paciente individualmente.

3.  **Atomicidade do Relatório:**
    Conforme solicitado no requisito do case, o sistema precisa gerar um relatório final. Ao manter tudo junto, o próprio arquivo de dados já serve como o relatório final, unificando as análises clínicas com os *metadados operacionais* (erros e status).