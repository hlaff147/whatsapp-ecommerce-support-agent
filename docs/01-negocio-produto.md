# PawDesk — Documento de Produto (Negócio)

> **Agente de IA para atendimento ao cliente de e-commerce pet via WhatsApp.**
> Versão 0.1 · Status: rascunho para validação · Idioma do produto: pt-BR
>
> **Nota:** projeto de portfólio. Todos os dados são sintéticos e todas as regras de negócio, metas e valores
> são **ilustrativos e parametrizáveis**. Em um cenário real, devem ser validados com Operações, Jurídico e DPO.

---

## 1. Resumo executivo

O **PawDesk** é um agente conversacional que atende, pelo WhatsApp, as dúvidas mais frequentes de clientes de um
e-commerce pet: **onde está meu pedido, qual o prazo, como faço uma troca, preciso da segunda via de nota/boleto
e qual produto é indicado para o meu pet**.

O agente consulta os sistemas da empresa em tempo real (pedidos, entregas, trocas, catálogo), executa ações
simples com confirmação do cliente e **transfere para um atendente humano, com o contexto completo**, sempre
que o caso for sensível, complexo ou o cliente pedir.

**Resultado esperado:** reduzir custo e tempo de atendimento sem piorar a experiência, liberando a equipe
humana para casos que exigem empatia e julgamento.

---

## 2. Contexto e problema

| Dor | Impacto |
|---|---|
| Alto volume de perguntas repetitivas (status, prazo, troca, 2ª via) | Fila longa e custo por atendimento elevado |
| Atendimento humano limitado ao horário comercial | Cliente espera horas por uma resposta simples |
| Informação espalhada em vários sistemas (pedido, transportadora, financeiro) | Atendente precisa navegar em várias telas |
| Picos sazonais (Black Friday, Natal, reposição mensal de ração) | Qualidade cai justamente quando a demanda sobe |
| Transferências sem contexto | Cliente precisa repetir tudo ao falar com o humano |

**Oportunidade:** uma parcela grande dessas conversas é de baixa complexidade e de resposta determinística
(os dados estão nos sistemas). Isso é o cenário ideal para automação com IA **com ferramentas** (o agente consulta
dados reais em vez de "adivinhar").

---

## 3. Objetivos e não-objetivos

### Objetivos
1. Resolver de ponta a ponta, sem humano, os casos de baixa complexidade (UC-01 a UC-06).
2. Responder em segundos, 24/7, com informação **correta e verificável**.
3. Fazer handoff para humano **com resumo e contexto**, sem que o cliente repita informações.
4. Proteger dados pessoais (LGPD) e a marca (sem promessas indevidas, sem orientação veterinária).
5. Ser **mensurável**: toda conversa gera métricas de qualidade, custo e latência.

### Não-objetivos (neste produto)
- Substituir o atendimento humano em casos sensíveis.
- Processar pagamentos ou coletar dados de cartão.
- Dar diagnóstico, prescrição ou orientação clínica veterinária.
- Fazer vendas ativas ou negociar descontos.

---

## 4. Personas

| Persona | Perfil | O que precisa | Canal/Contexto |
|---|---|---|---|
| **Marina, a tutora recorrente** | 34 anos, 2 gatos, compra ração todo mês | Saber se o pedido chega a tempo; repor sem esforço | WhatsApp, rápida, no celular |
| **Carlos, o tutor de primeira viagem** | 27 anos, comprou um filhote | Escolher produto certo; tirar dúvidas básicas | Mensagens longas, inseguro |
| **Bia, a cliente insatisfeita** | Pedido atrasado ou produto errado | Solução rápida e ser ouvida | Tom irritado, quer humano |
| **Rafael, o atendente (usuário interno)** | Opera a fila de suporte | Receber o caso já resumido e organizado | Painel de helpdesk |
| **Helena, a gestora de CX** | Responsável por custo e satisfação | Métricas, controle e confiança no agente | Dashboards |

---

## 5. Proposta de valor

- **Para o cliente:** resposta imediata, sem fila, no canal que ele já usa.
- **Para o atendente:** menos tickets repetitivos; casos transferidos chegam resumidos.
- **Para o negócio:** menor custo por atendimento, mais capacidade nos picos e dados estruturados sobre as dores dos clientes.

---

## 6. Escopo

### 6.1 MVP (dentro do escopo)

| ID | Caso de uso | Tipo |
|---|---|---|
| UC-01 | Consultar status e rastrear pedido | Consulta |
| UC-02 | Informar prazo de entrega (por CEP e de um pedido existente) | Consulta |
| UC-03 | Solicitar troca/devolução | Ação com confirmação |
| UC-04 | Segunda via de nota fiscal | Consulta sensível |
| UC-05 | Segunda via de boleto/PIX | Consulta sensível |
| UC-06 | Dúvidas e recomendação de produto | Consulta/consultiva |
| UC-07 | Falar com atendente (handoff) | Controle |
| UC-08 | Fora de escopo e saúde pet (resposta segura + encaminhamento) | Controle |

### 6.2 Fora do MVP (backlog)
Cancelamento de pedido, alteração de endereço após despacho, planos de saúde pet, creche/hospedagem,
voz (áudios), envio de fotos para análise de defeito, notificações proativas, outros canais além do WhatsApp.

---

## 7. Jornadas e casos de uso

### UC-01 — "Onde está meu pedido?"
**Gatilho:** cliente pergunta sobre pedido, entrega ou rastreio.
**Fluxo:** identifica o cliente pelo telefone → localiza o pedido (cita o número ou lista os últimos) →
consulta status e rastreio → responde com status, última movimentação e previsão.
**Exceções:** pedido não encontrado; pedido de outra pessoa; entrega atrasada (ver RN-04).

```
Cliente: oi, cadê meu pedido da ração?
PawDesk: Oi, Marina! 🐾 Encontrei seu pedido PD-104822 (Ração Premium Gatos 10kg).
         Ele saiu para entrega hoje às 08:40 e a previsão é até as 18h.
         Quer que eu te mande o link de rastreio?
```

### UC-02 — "Qual o prazo?"
**Antes da compra:** cliente informa CEP e produto → agente retorna prazo e frete estimados pelo sistema.
**Depois da compra:** prazo vem do pedido/transportadora. O agente **nunca estima prazo por conta própria**.

### UC-03 — Troca ou devolução
**Fluxo:** entende o motivo → exige verificação reforçada (RN-01) → checa elegibilidade pelas regras →
resume o que será aberto → **cliente confirma por botão** → abre a solicitação → informa protocolo e próximos passos.

```mermaid
flowchart TD
    A[Cliente pede troca] --> B{Identidade reforçada?}
    B -- não --> B1[Pedir nº do pedido + 3 últimos dígitos do CPF]
    B1 --> B
    B -- sim --> C[Coletar item e motivo]
    C --> D{Elegível pelas regras?}
    D -- não --> D1[Explicar motivo e alternativas]
    D1 --> D2{Cliente insiste?}
    D2 -- sim --> H[Handoff humano]
    D2 -- não --> Z[Encerrar]
    D -- sim --> E{Valor acima do limite?}
    E -- sim --> H
    E -- não --> F[Resumir e pedir confirmação por botão]
    F -- confirmou --> G[Abrir solicitação e enviar protocolo]
    F -- cancelou --> Z
    G --> Z
```

### UC-04 / UC-05 — Segunda via (NF e boleto/PIX)
Exigem verificação reforçada. A entrega é feita por **link assinado com validade curta** (RN-11); o agente não
reproduz dados fiscais completos na conversa.

### UC-06 — Dúvidas e recomendação de produto
O agente usa o catálogo ativo e em estoque. Pergunta o essencial (espécie, porte, idade, restrições informadas
pelo tutor) e recomenda 1 a 3 produtos com o porquê. Não faz alegações terapêuticas (RN-15).

### UC-07 — Falar com atendente
Cliente pede humano, demonstra frustração ou o agente não consegue resolver → handoff conforme a seção 9.

### UC-08 — Fora de escopo e saúde pet
Perguntas como *"meu cachorro comeu chocolate, e agora?"* recebem uma **resposta segura e padronizada**:
sem diagnóstico, orientação de procurar um veterinário imediatamente e, quando existir, oferta de encaminhar
para o canal veterinário da empresa.

---

## 8. Regras de negócio

> Valores entre parênteses são **parâmetros configuráveis**, não constantes de código.

| ID | Regra |
|---|---|
| **RN-01** | **Identidade em dois níveis.** *Nível 1:* telefone do WhatsApp coincide com o cadastro → permite consultas de status. *Nível 2 (reforçada):* nº do pedido + 3 últimos dígitos do CPF → necessário para ações (troca) e documentos (NF, boleto). Máx. 3 tentativas; depois, handoff e bloqueio temporário (30 min). |
| **RN-02** | O cliente só acessa dados dos **próprios** pedidos. O agente nunca revela dados de terceiros. |
| **RN-03** | Status, prazo, valores e protocolos **sempre** vêm dos sistemas. O agente nunca inventa, estima ou "arredonda". |
| **RN-04** | Pedido atrasado (hoje > previsão): reconhecer o atraso, informar a última movimentação e abrir/consultar ocorrência. Atraso acima de (3 dias úteis) → handoff. |
| **RN-05** | **Arrependimento:** até (7 dias corridos) após o recebimento em compras online, com reembolso integral (referência: CDC, art. 49 — *validar com Jurídico*). |
| **RN-06** | **Defeito, avaria ou item errado:** até (30 dias) após o recebimento, com troca ou reembolso. |
| **RN-07** | *Exemplo:* troca por palatabilidade de ração, 1 vez por cliente/SKU, em até (15 dias) e com embalagem preservada. *Definir com Operações.* |
| **RN-08** | *Exemplo de itens não elegíveis:* medicamentos controlados ou refrigerados, itens personalizados, higiene com lacre violado. |
| **RN-09** | Troca/reembolso acima de (R$ 500) exige aprovação humana → handoff. |
| **RN-10** | Toda ação com efeito (abrir troca) exige **confirmação explícita do cliente por botão**. |
| **RN-11** | Nota fiscal e boleto são entregues por **link assinado** com validade de (15 min). |
| **RN-12** | 2ª via de boleto/PIX apenas para pedidos com pagamento pendente. Outros cenários → handoff. |
| **RN-13** | O agente **não promete** reembolso, prazo ou exceção fora do que as ferramentas retornam, **não negocia** desconto e **não cita** políticas que não estejam cadastradas. |
| **RN-14** | **Saúde pet:** não diagnostica, não prescreve e não indica dose. Em sinais de emergência, orienta procurar um veterinário imediatamente. |
| **RN-15** | Recomendações usam apenas catálogo ativo e em estoque, sem alegações terapêuticas. |
| **RN-16** | **Janela de 24h do WhatsApp:** fora dela, só mensagens *template* aprovadas. |
| **RN-17** | **LGPD:** coleta mínima, CPF nunca armazenado por completo, logs com dados pessoais mascarados, retenção definida com o DPO. |
| **RN-18** | O agente opera 24/7. Humanos atendem em horário comercial; fora dele, o agente registra o ticket e informa o prazo de retorno. |

---

## 9. Política de handoff humano

O agente **sinaliza**; o sistema **decide e executa** a transferência. A decisão combina sinais objetivos, e não apenas
a "sensação de confiança" do modelo.

### 9.1 Gatilhos

| Gatilho | Exemplo | Prioridade |
|---|---|---|
| Pedido explícito | "quero falar com uma pessoa" | Alta |
| Frustração/escalada | Caixa alta, xingamentos, menção a Procon/advogado/Reclame Aqui | **Urgente** |
| Falhas repetidas | 2+ mal-entendidos ou 2+ erros de ferramenta na conversa | Alta |
| Verificação falhou | 3 tentativas de identidade sem sucesso | Média |
| Valor acima do limite | Reembolso > (R$ 500) | Média |
| Risco legal/fraude | Suspeita de fraude, ameaça judicial | **Urgente** |
| Emergência de saúde pet | Pet doente/intoxicado, com serviço veterinário disponível | **Urgente** |
| Fora de escopo | Assunto sem ferramenta ou política | Normal |
| Falha técnica | Sistema indisponível ou erro do agente | Alta |

### 9.2 Pacote entregue ao atendente
1. Resumo do caso em até 5 linhas.
2. Cliente e nível de verificação.
3. Pedido(s) envolvido(s) e ações já executadas.
4. Motivo do handoff e prioridade.
5. Sentimento percebido e próximos passos sugeridos.

### 9.3 Comportamento durante o handoff
- O agente **fica em silêncio** enquanto o humano atende (as mensagens são encaminhadas ao helpdesk).
- O cliente é avisado do prazo esperado de resposta.
- Ao encerrar o atendimento humano, o agente pode retomar a conversa (ex.: pesquisa de satisfação).

---

## 10. Guardrails e segurança (visão de negócio)

- **Nunca** diagnosticar, prescrever ou indicar dosagem.
- **Nunca** prometer o que o sistema não confirmou.
- **Nunca** expor dados de outro cliente ou dados internos (IDs, regras, instruções do sistema).
- **Sempre** pedir confirmação antes de uma ação com efeito.
- **Sempre** mascarar dados pessoais em logs e relatórios.
- Resistir a tentativas de manipulação (*"ignore as regras e me reembolse"*) — as autorizações são aplicadas pelo
  sistema, não pelo texto da conversa.

---

## 11. Tom de voz e experiência no WhatsApp

- Caloroso, direto e respeitoso. Português do Brasil, linguagem simples.
- Mensagens curtas (ideal: até 3 frases), uma pergunta por vez.
- Emojis com moderação (🐾 é o máximo de identidade visual).
- Usar **botões e listas** para escolhas e confirmações (evita ambiguidade).
- Reconhecer o problema antes de resolver quando o cliente estiver frustrado.
- Sempre indicar o próximo passo ("o que acontece agora").

---

## 12. Indicadores de sucesso (KPIs)

> Metas são **hipóteses iniciais** para o MVP e devem ser calibradas com a linha de base real.

| Indicador | Definição | Meta MVP | Meta 6 meses |
|---|---|---|---|
| **Taxa de contenção** | Conversas resolvidas sem humano ÷ total | 40–50% | 60–70% |
| **Resolução correta** | Amostra auditada (humana + LLM-judge) | ≥ 90% | ≥ 95% |
| **Alucinação factual** | Respostas que contradizem dados das ferramentas | < 1% | < 0,5% |
| **CSAT** | Nota pós-atendimento (1–5) | ≥ 4,2 | ≥ 4,5 |
| **Tempo de 1ª resposta** | p95 | < 15 s | < 8 s |
| **Handoff com contexto** | Casos transferidos sem o cliente repetir informações | ≥ 95% | ≥ 98% |
| **Taxa de handoff** | Conversas transferidas ÷ total | 50–60% | 30–40% |
| **Custo por conversa (IA)** | LLM + infraestrutura ÷ conversas | Medir | Reduzir 30% |
| **Incidentes de privacidade** | Vazamentos ou acessos indevidos | 0 | 0 |
| **Acerto de ferramenta** | Tool correta + argumentos corretos (evalset) | ≥ 95% | ≥ 98% |

### Economia unitária (modelo de cálculo)

```
custo_ia_por_conversa  = Σ(tokens_entrada × preço_in + tokens_saída × preço_out por modelo) + infra_rateada
economia_por_conversa  = taxa_contenção × (custo_humano_por_atendimento − custo_ia_por_conversa)
                         − (1 − taxa_contenção) × custo_ia_por_conversa     # custo "perdido" quando há handoff
```

Meta de negócio: manter `custo_ia_por_conversa` **muito abaixo** do custo humano por atendimento e monitorar
semanalmente por caso de uso.

---

## 13. Roadmap

| Fase | Foco | Entregas |
|---|---|---|
| **0 — Descoberta** | Dados e regras | Levantamento de top motivos de contato, regras reais, base de conversas, definição de KPIs |
| **1 — MVP leitura** | UC-01, UC-02, UC-07, UC-08 | Agente com consultas, handoff com contexto, guardrails, evals e painel de métricas |
| **2 — Ações** | UC-03, UC-04, UC-05 | Verificação reforçada, troca com confirmação por botão, links assinados |
| **3 — Consultivo** | UC-06 | Catálogo, recomendação por perfil do pet, melhoria de recorrência |
| **4 — Escala** | Canais e otimização | Notificações proativas (atraso, reposição), áudio/foto, A/B de prompts, roteamento de modelos por custo |

---

## 14. Riscos e mitigações

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Alucinação sobre status/prazo | Média | Alto | Dados somente via ferramentas; guardrail de saída; evals de regressão |
| Vazamento de dados pessoais | Baixa | Crítico | Verificação em 2 níveis, autorização no sistema (não no prompt), mascaramento, auditoria |
| Cliente irritado preso no bot | Média | Alto | Gatilhos de handoff objetivos; "falar com atendente" sempre disponível |
| Abuso/prompt injection | Média | Médio | Validação de entrada e saída, ferramentas sem parâmetro de identidade |
| Custo de LLM escala sem controle | Média | Médio | Roteamento por modelo, limites por conversa, monitoramento de custo |
| Mensagens duplicadas/fora de ordem | Alta | Médio | Idempotência, fila e bloqueio por conversa |
| Indisponibilidade de sistemas internos | Média | Médio | Timeouts, retentativas, fallback para handoff |
| Orientação veterinária indevida | Baixa | Alto | Regra RN-14, saída padronizada e teste dedicado |

---

## 15. Critérios de aceite do MVP

- [ ] UC-01, UC-02, UC-07 e UC-08 funcionando de ponta a ponta no canal WhatsApp (ou simulador).
- [ ] Nenhuma resposta de status/prazo/valor sem origem em ferramenta (verificado por evals).
- [ ] Handoff entrega resumo e contexto; agente fica em silêncio durante o atendimento humano.
- [ ] Conjunto de avaliação (≥ 60 conversas de referência) com metas de **acerto de ferramenta ≥ 95%** e **resolução correta ≥ 90%**.
- [ ] Testes de segurança: acesso a pedido de outro cliente, prompt injection, pedido de diagnóstico veterinário.
- [ ] Painel com contenção, handoff, latência e custo por conversa.
- [ ] Logs sem dados pessoais em texto aberto.

---

## 16. Partes interessadas

| Papel | Responsabilidade |
|---|---|
| Produto | Escopo, priorização, KPIs |
| Operações/CX | Regras de troca, tom de voz, fila de handoff |
| Engenharia | Arquitetura, integrações, qualidade e custo |
| Jurídico/DPO | Políticas de consumidor, LGPD, retenção |
| Dados | Métricas, avaliação e curadoria do dataset de conversas |

---

## 17. Glossário

| Termo | Significado |
|---|---|
| **Handoff** | Transferência da conversa do agente para um atendente humano |
| **Contenção** | Conversa resolvida sem intervenção humana |
| **Step-up (verificação reforçada)** | Validação adicional de identidade para ações sensíveis |
| **Tool (ferramenta)** | Função que o agente chama para consultar ou executar algo nos sistemas |
| **Guardrail** | Regra que limita o que o agente pode dizer ou fazer |
| **Template (WhatsApp)** | Mensagem pré-aprovada usada fora da janela de 24h |
| **LLM-judge** | Modelo usado para avaliar a qualidade das respostas |

---

## 18. Perguntas em aberto

1. Quais são os 10 principais motivos de contato e seu volume real?
2. As regras de troca por categoria (ração, acessório, higiene) estão formalizadas e atualizadas?
3. Qual helpdesk será integrado e qual o SLA humano por prioridade?
4. Existe canal veterinário para encaminhar emergências (UC-08)?
5. Qual a política de retenção de conversas definida pelo DPO?
6. O telefone do WhatsApp é um identificador confiável no cadastro?
