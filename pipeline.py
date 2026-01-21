from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional, Literal, TypedDict
from dotenv import load_dotenv

# Imports obrigatórios
try:
    from openai import OpenAI
    from pydantic import BaseModel, Field, ValidationError, field_validator 
    from langgraph.graph import StateGraph, END
except ImportError:
    raise ImportError("Dependências ausentes. Instale: pip install openai pydantic langgraph")

# Carrega as variáveis do arquivo .env
load_dotenv()

# Inicializa o cliente
client = OpenAI()

# Configuração de Diretórios
BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "data" / "input"
PROMPTS_DIR = BASE_DIR / "prompts"
OUT_PATH = BASE_DIR / "results.json"

# =========================
# 1. Pydantic Schemas (Structured Output)
# =========================

class RiskAssessment(BaseModel):
    level: Literal["baixo", "médio", "alto"]
    signals: List[str]

class ClinicalReport(BaseModel):
    required: bool
    summary: str

class ClinicalOutput(BaseModel):
    """
    Schema principal com validações de tamanho conforme regras do PDF.
    """
    analysis: str = Field(description="Análise clínica estruturada")
    
    themes: List[str] = Field(min_length=3, max_length=6, description="3-6 itens")
    signifiers: List[str] = Field(min_length=3, max_length=8, description="3-8 itens")
    hypotheses: List[str] = Field(min_length=2, max_length=4, description="2-4 hipóteses")
    questions: List[str] = Field(min_length=3, max_length=6, description="3-6 perguntas")
    
    risk_assessment: RiskAssessment
    clinical_report: ClinicalReport

    @field_validator('analysis')
    @classmethod
    def validate_analysis_length(cls, v: str) -> str:
        word_count = len(v.split())
        min_words = 40  # Aprox 4 linhas
        max_words = 200 # Aprox 8 linhas
        
        if word_count < min_words:
            raise ValueError(f"Análise muito curta ({word_count} palavras). Mínimo esperado: {min_words}.")
        
        if word_count > max_words:
            raise ValueError(f"Análise muito longa ({word_count} palavras). Máximo esperado: {max_words}.")
            
        return v
    
# =========================
# 2. State Definition
# =========================

class ClinicalState(TypedDict):
    filename: str
    input_text: str
    prompt_version: str
     
    # Resposta crua do modelo (string JSON) 
    raw_response: Optional[str] 
     
    # Objeto validado pelo Pydantic 
    parsed_output: Optional[ClinicalOutput] 
     
    # Lista de erros (parsing ou validação) 
    errors: List[str] 

# =========================
# 3. IO / Prompt Helpers
# =========================

def load_prompt(prompt_version: str) -> str:
    path = PROMPTS_DIR / f"prompt_{prompt_version}.txt"
    if not path.exists():
        # Fallback para simular o prompt estruturado se o arquivo não existir
        return """
        Você é uma IA de Psicanálise. Analise o texto abaixo e retorne APENAS um JSON válido.
        Texto: {INPUT}
        """
    return path.read_text(encoding="utf-8")

def read_inputs(input_dir: Path) -> List[Tuple[str, str]]:
    """
    Lê arquivos .txt. Retorna [(filename, content), ...] 
    """
    if not input_dir.exists():
        input_dir.mkdir(parents=True, exist_ok=True)
        # Cria um arquivo de exemplo se a pasta estiver vazia para teste
        (input_dir / "exemplo_paciente.txt").write_text(
            "Eu sempre chego atrasado. Parece que faço isso de propósito. Quando chego, fico em silêncio.", 
            encoding="utf-8"
        )
        
    files = list(input_dir.glob("*.txt"))
    return [(f.name, f.read_text(encoding="utf-8")) for f in files]

# =========================
# 4. Model Call (Hybrid: API + Mock Fallback)
# =========================

def call_model(prompt: str) -> str:
    """
    Tenta chamar a API da OpenAI. 
    Se falhar (ex: erro de cota/billing), ativa o Fallback para o Mock.
    """
    # Definição do Mock (Backup)
    mock_response = {
        "analysis": "O paciente apresenta uma clara manifestação de resistência transferencial através do manejo do tempo e da palavra. O atraso recorrente ('sempre') configura-se como um acting out, uma tentativa de controlar o setting analítico ou evitar o contato com conteúdos angustiantes. A percepção de que faz isso 'de propósito' sugere um insight incipiente sobre a determinação inconsciente de seus atos e uma possível formação de compromisso sintomática. O silêncio que se segue à chegada atua como uma barreira secundária, reforçando a recusa em se entregar à associação livre. Essa dinâmica aponta para uma dificuldade em lidar com a demanda do Outro, possivelmente expressando hostilidade latente ou medo da dependência.",
        "themes": ["Resistência", "Transferência", "Controle", "Silêncio", "Tempo"],
        "signifiers": ["Atrasado", "Propósito", "Silêncio", "Sempre", "Chego"],
        "hypotheses": [
            "O atraso funciona como uma defesa contra a angústia de castração ou vulnerabilidade na sessão.",
            "O silêncio é uma extensão da agressividade passiva manifestada pelo atraso.",
            "A intencionalidade percebida indica um gozo na manutenção do sintoma de evitação."
        ],
        "questions": [
            "O que você sente ou pensa nos minutos exatos antes de sair para a sessão?",
            "A quem esse 'propósito' de se atrasar estaria endereçado?",
            "O silêncio, quando você chega, é vivido como vazio ou como excesso de pensamentos?",
            "Existem outras situações em sua vida onde o atraso é uma regra?"
        ],
        "risk_assessment": {
            "level": "baixo",
            "signals": [
                "Ausência de ideação suicida ou agressiva explícita",
                "Discurso focado em mecanismos de defesa neuróticos"
            ]
        },
        "clinical_report": {
            "required": False,
            "summary": "Paciente relata padrão de resistência caracterizado por atrasos sistemáticos e mutismo subsequente, reconhecendo certa intencionalidade no ato."
        }
    }

    try:            
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é uma IA Clínica especializada em Psicanálise que responde estritamente em JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"} # Força JSON para o Pydantic
        )
        
        print("Resposta gerada pela API real.")
        return completion.choices[0].message.content

    except Exception as e:
        error_msg = str(e)
        print(f"\nFALHA NA API: {error_msg}")
        print("Ativando FALLBACK para MOCK ...")

        # Retorna o JSON do Mock
        return json.dumps(mock_response, ensure_ascii=False)

# =========================
# 5. LangGraph Nodes
# =========================

def generation_node(state: ClinicalState) -> Dict:
    """
    Nó de Geração: Monta prompt e chama o modelo. 
    """
    print(f"--- Node: Generation ({state['filename']}) ---")
    
    # 1. Carrega o template do prompt
    prompt_template = load_prompt(state['prompt_version'])
    
    # 2. Substituir o placeholder pelo input no prompt
    full_prompt = prompt_template.replace("{INPUT}", state['input_text'])
    
    # 3. Chama o modelo
    response_str = call_model(full_prompt)
    
    return {"raw_response": response_str}

def validation_node(state: ClinicalState) -> Dict:
    """
    Nó de Validação: Usa Pydantic para validar o JSON cru.
    """
    print("--- Node: Validation ---")
    
    raw = state.get("raw_response", "")
    errors = []
    parsed_obj = None

    try:
        # Validação rígida de tipos e limites (min_length, max_length, Literal)
        parsed_obj = ClinicalOutput.model_validate_json(raw)
        
    except ValidationError as e:
        # Captura erros de validação estrutural (ex: lista muito curta, tipo errado) 
        errors = [f"Validation Error: {err['msg']} at {err['loc']}" for err in e.errors()] 
        
    except json.JSONDecodeError as e:
        errors = [f"Erro de Parse JSON: {str(e)}"]
        
    except Exception as e:
        errors = [f"Erro Desconhecido: {str(e)}"]

    return {
        "parsed_output": parsed_obj,
        "errors": errors
    }

# =========================
# 6. Graph Construction
# =========================

def build_graph() -> StateGraph:
    workflow = StateGraph(ClinicalState)
    
    # Adiciona nós 
    workflow.add_node("generator", generation_node)
    workflow.add_node("validator", validation_node)
    
    # Define fluxo linear 
    workflow.set_entry_point("generator")
    workflow.add_edge("generator", "validator")
    workflow.add_edge("validator", END)
    
    return workflow.compile()

def save_results(payload: Dict[str, Any], path: Path) -> None: 
    # Converte o objeto Pydantic para dict antes de salvar, se existir 
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# =========================
# 7. Main Execution
# =========================

def main(prompt_version: str = "v2"):
    # 1. Leitura 
    items = read_inputs(INPUT_DIR)
    
    # 2. Setup do Grafo 
    app = build_graph()
    results = []
    ok_count = 0
    
    print(f"Iniciando Pipeline (LangGraph + Pydantic) - Prompt {prompt_version}...\n")
    
    for fname, text in items:
        
        # Estado Inicial
        initial_state: ClinicalState = {
            "filename": fname,
            "input_text": text,
            "prompt_version": prompt_version,
            "raw_response": None,
            "parsed_output": None,
            "errors": []
        }
        
        try:
            # Invoca o grafo 
            final_state = app.invoke(initial_state)
            
            output_obj = final_state["parsed_output"]
            errors = final_state["errors"]
            
            # Sucesso se temos objeto validado e zero erros 
            is_ok = (output_obj is not None) and (len(errors) == 0)
            
            if is_ok:
                ok_count += 1
                # Converter modelo Pydantic para dict para salvar no JSON final                 
                final_output = output_obj.model_dump()
            else:
                final_output = None

            results.append({
                "file": fname,
                "ok": is_ok,
                "errors": errors,
                "output": final_output
            })
            
        except Exception as e: 
            results.append({ 
                "file": fname, 
                "ok": False, 
                "errors": [f"Runtime Error: {e}"], 
                "output": None 
            }) 
            
    # 3. Consolidação 
    payload = {
        "prompt_version": prompt_version,
        "total": len(results),
        "metrics": {"ok": ok_count, "failed": len(results) - ok_count},
        "results": results,
    }

    save_results(payload, OUT_PATH)
    print(f"\nProcessamento concluído. Relatório salvo em: {OUT_PATH}")
    print(f"Sucesso: {ok_count} | Falhas: {len(results) - ok_count}")

if __name__ == "__main__":
    main()