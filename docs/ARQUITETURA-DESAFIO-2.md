# Arquitetura proposta — Desafio Técnico 2

O Desafio 2 não foi escolhido para implementação. Esta proposta registra a arquitetura que seria discutida na entrevista técnica.

## Leitura do material fornecido

A pasta disponibilizada contém 50 PDFs distribuídos entre os três tipos previstos no enunciado: documentos fiscais, contratos de prestação de serviços e relatórios de manutenção.

Nas amostras inspecionadas, os PDFs são digitalizações em imagem e não possuem texto extraível diretamente. Isso torna OCR/visão uma etapa real do problema, não apenas uma hipótese arquitetural.

Também há variações de layout e de título dentro de uma mesma classe, então a classificação não deve depender apenas de palavras fixas no cabeçalho.

## Fluxo proposto

```text
PDF
 |
 v
ingestão + hash
 |
 +--> documento já processado? --> resultado existente
 |
 v
detecção de texto nativo
 |
 +--> texto disponível ------+
 |                           |
 +--> imagem --> OCR/visão --+
                             |
                             v
                       classificação
                             |
          +------------------+------------------+
          |                  |                  |
          v                  v                  v
      nota fiscal        contrato         manutenção
          |                  |                  |
          +-------- extração estruturada ------+
                             |
                             v
                    validação com Pydantic
                             |
              +--------------+--------------+
              |                             |
              v                             v
         persistência                  revisão / DLQ
```

## Etapas

**Ingestão e idempotência.** Cada arquivo recebe identificador e hash antes do processamento. Reexecuções não duplicam registros e permitem retomar lotes interrompidos.

**Extração de conteúdo.** Primeiro é verificado se existe texto nativo aproveitável. OCR ou modelo de visão é acionado somente quando necessário, reduzindo custo e latência.

**Classificação.** O classificador retorna o tipo do documento e confiança. Casos abaixo de um limiar seguem para revisão, em vez de serem roteados silenciosamente para o extrator errado.

**Roteamento e extração.** Cada classe possui um contrato Pydantic próprio para os campos exigidos pelo desafio. O modelo retorna saída estruturada e a aplicação valida tipos, campos obrigatórios e consistência básica.

**Persistência.** O resultado inclui dados extraídos, tipo, confiança, versão do extrator, hash do arquivo e estado do processamento. Isso permite auditoria e reprocessamento controlado.

## Escala para milhões de documentos

A execução seria orientada a jobs, com armazenamento de objetos e fila entre as etapas. Workers independentes permitem escalar OCR e extração conforme o gargalo real.

Retries seriam limitados e diferenciados por categoria de erro. Arquivos anômalos ou repetidamente inválidos seguiriam para uma fila de exceções, sem interromper o lote.

O LLM não seria usado como orquestrador de toda a infraestrutura. Hash, filas, retries, persistência, validação e idempotência são determinísticos. Modelos entram apenas onde há valor semântico: OCR/visão quando necessário, classificação e extração.

## Custo e confiabilidade

- evitar OCR quando o PDF já contém texto utilizável;
- processar páginas somente quando necessárias;
- usar modelo menor para classificação e escalar para modelo mais capaz apenas em baixa confiança;
- versionar prompts, schemas e modelos;
- registrar latência, custo, confiança e taxa de revisão por etapa;
- manter amostras de avaliação por classe para detectar regressões.

## Reprodutibilidade

A mesma versão de pipeline deve produzir o mesmo contrato de saída para a mesma entrada. Componentes probabilísticos são cercados por validação estruturada, parâmetros controlados, versões registradas e avaliações de regressão.

Essa separação mantém o pipeline observável e recuperável sem transformar o processamento documental em um fluxo agentivo desnecessariamente complexo.
