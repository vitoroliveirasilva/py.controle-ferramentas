# Guia operacional para usuários

## Entrada no sistema

1. Acesse a URL do sistema
2. Clique em entrar
3. Autentique com a conta Microsoft corporativa
4. Caso apareça acesso negado, acione o administrador do sistema

## Cadastros básicos

### Categorias

Use para classificar ferramentas, como:

- elétrica;
- hidráulica;
- medição;
- calibração;
- segurança;
- mecânica.

### Locais

Use para representar:

- filial;
- oficina;
- almoxarifado;
- site de cliente;
- departamento;
- manutenção/calibração.

### Ferramentas

Cadastre:

- código interno;
- nome;
- categoria;
- número de série quando aplicável;
- ativo imobilizado quando houver;
- criticidade;
- controle individual;
- necessidade de calibração;
- foto de referência quando disponível.

## Custódia

Toda ferramenta ativa deve ter custódia atual ou status que justifique ausência de responsável.

Fluxo:

1. Cadastre a ferramenta
2. Defina custódia inicial
3. Altere custódia apenas por troca controlada ou transferência formal
4. Consulte a linha do tempo sempre que houver dúvida

## Transferências

1. Crie transferência informando ferramenta e destino
2. Confirme origem
3. Confirme destino
4. Se recusada ou cancelada, a custódia anterior é preservada

Nunca use transferência para ferramenta baixada, inativa, em inventário ou com pendência crítica sem regra específica.

## Inventários

1. Abra inventário por local ou técnico
2. Inicie conferência
3. Marque cada item:
   - encontrado;
   - faltante;
   - danificado;
   - substituído;
   - não aplicável.
4. Regularize divergências
5. Envie para assinatura
6. Assine/finalize quando tudo estiver resolvido

## Divergências

Divergência aberta impede finalização.

Ações possíveis:

- recontar;
- justificar com aprovação;
- abrir ocorrência;
- transferir;
- cadastrar excedente;
- vincular responsável correto;
- baixar por perda;
- registrar dano;
- registrar substituição;
- reintegrar ferramenta;
- cancelar processo com motivo.

## Ocorrências

Use para registrar:

- perda;
- extravio;
- dano;
- substituição;
- baixa;
- manutenção;
- calibração;
- reintegração;
- regularização cadastral.

Anexe fotos/documentos quando necessário.

## Assinaturas

A assinatura registra evidência de confirmação de ação crítica e não armazena senha.

## Relatórios

Use relatórios para:

- situação atual;
- histórico por ferramenta;
- inventários;
- divergências;
- transferências;
- ocorrências;
- ativos imobilizados.

Exportações respeitam permissões e podem gerar auditoria.

## Notificações

As notificações apontam pendências:

- inventário vencido;
- transferência pendente;
- assinatura pendente;
- divergência crítica.

## QR Code e operação mobile

- Use a etiqueta QR para localizar rapidamente uma ferramenta
- Use tela de leitura do inventário em campo
- Anexe evidências no item conferido

## Transferências robustas

- A criação de transferência coloca a ferramenta em status `transferencia` e bloqueia nova transferência pendente para a mesma ferramenta
- A confirmação de origem só deve ser feita por usuário relacionado à custódia de origem ou por perfil com `transfers.override`
- A confirmação de destino só deve ser feita pelo destinatário, por usuário com escopo do local destino ou por perfil com `transfers.override`
- Transferência concluída não deve ser cancelada. Para correção operacional, abra uma transferência reversa ou ocorrência administrativa com justificativa
- Transferências pendentes podem expirar com segurança. A expiração restaura o status anterior dos itens ainda abertos e registra auditoria
- O parâmetro `TRANSFER_EXPIRATION_DAYS` define o prazo padrão de expiração automática/manual de transferências pendentes

## Inventários e divergências robustas

- A leitura de um código que não está na lista esperada passa a registrar ferramenta excedente quando o código, ativo ou série existir no cadastro
- Ferramenta excedente gera item de inventário com status `excedente` e divergência aberta
- Ferramenta baixada encontrada, ferramenta em transferência pendente ou custódia diferente do escopo geram tipos específicos de divergência
- Regularização por `transferir` exige vínculo com uma transferência existente que contenha a ferramenta
- Regularização por perda, dano, substituição, reintegração ou ocorrência abre ou vincula ocorrência operacional/patrimonial
- Recontagem não fecha uma divergência enquanto o item continuar em status divergente
- Inventário não deve ser enviado para assinatura enquanto houver item pendente ou divergência aberta

## Uploads, downloads e exportações sensíveis

- Fotos de referência, evidências de inventário e anexos de ocorrência devem ser enviados apenas pelos formulários autenticados
- Arquivos sensíveis não devem ser colocados em `static`; o armazenamento padrão é `UPLOAD_BASE_DIR`
- Downloads de evidências e anexos passam por permissão e escopo antes de entregar o arquivo
- Uploads validam extensão, tamanho, MIME e assinatura básica do conteúdo para PDF/imagens
- Se a gravação no banco falhar após salvar o arquivo, o arquivo físico é removido para evitar órfãos
- Exportações CSV/XLSX respeitam os mesmos filtros e escopos da tela
- Valores iniciados com `=`, `+`, `-` ou `@` são neutralizados em CSV/XLSX para reduzir risco de formula injection
- Exportações são limitadas por `REPORT_EXPORT_MAX_ROWS`; refine os filtros quando o limite for atingido
- Downloads e exportações sensíveis são auditados sem registrar conteúdo bruto do arquivo

## Envio de e-mails via Brasif Gateway

O envio de e-mails operacionais deve usar exclusivamente o Brasif Gateway Microsoft Graph. Portanto, não configure SMTP.

A tela de notificações permite processar pendências e registrar o histórico de entrega por tentativa.

Cuidados operacionais:

- configure `NOTIFICATIONS_EMAIL_ENABLED=1` somente com `BRASIF_GATEWAY_API_KEY`;
- valide `BRASIF_GATEWAY_BASE_URL=https://howard.brasif.local`;
- use `BRASIF_GATEWAY_TIMEOUT_SECONDS` para evitar requests presos;
- retries são aplicados apenas para timeout, 408, 429 e 5xx;
- erros 401/403 e 422 não são repetidos;
- auditoria registra assunto, contagem de destinatários, HTTP status, duração e erro resumido;
- API key, headers completos, corpo sensível e anexos não devem ser registrados em claro.
