# Critérios de aceite do MVP

## Autenticação e autorização

- O usuário deve autenticar pela Microsoft
- O usuário só deve acessar se existir no BD
- Usuário inativo, bloqueado ou removido logicamente não deve acessar
- Usuário sem permissão não deve executar ação protegida
- Botão oculto em tela não substitui validação backend

## Cadastros

- O sistema deve permitir cadastrar categorias, locais, usuários e ferramentas
- Código interno deve ser único
- Ativo imobilizado deve ser único quando preenchido
- Alterações críticas devem exigir motivo e registrar auditoria
- Inativação deve ser preferida a exclusão física

## Custódia

- Ferramenta ativa deve ter custódia atual ou status que justifique ausência
- Ferramenta não pode ter duas custódias atuais
- Troca de custódia deve gerar linha do tempo
- Histórico deve permitir reconstruir posse

## Transferência

- Transferência deve ter origem, destino, motivo e item(ns)
- Recusa deve preservar custódia anterior
- Cancelamento deve preservar histórico
- Conclusão deve atualizar custódia
- Ações críticas devem gerar assinatura/evidência quando aplicável

## Inventário

- Inventário deve comparar esperado com encontrado
- Deve permitir rascunho e andamento
- Divergência deve ser criada para item faltante/danificado/excedente/substituído
- Inventário com divergência aberta não pode ser finalizado
- Finalização deve exigir assinatura interna
- Relatório finalizado deve preservar evidências

## Ocorrências

- Deve registrar perda, extravio, dano, substituição, baixa, manutenção, calibração, reintegração e regularização
- Ocorrência patrimonial deve registrar impacto e decisão
- Aprovação deve alterar status da ferramenta quando aplicável
- Anexos devem respeitar tamanho, extensão e MIME permitido

## Assinaturas

- Deve registrar usuário, data/hora, ação, entidade, método, resultado, IP, user-agent e contexto
- Não deve armazenar senha
- Usuário inativo/bloqueado não pode assinar

## Relatórios

- Situação atual deve listar ferramenta, status e custódia
- Histórico por ferramenta deve listar linha do tempo
- Relatórios devem respeitar permissão e escopo
- Exportações sensíveis devem gerar auditoria
- CSV/XLSX deve neutralizar formula injection
- Exportações grandes devem respeitar limite configurado

## Notificações

- Sistema deve gerar notificações internas para pendências críticas
- E-mail deve ser opcional
- E-mail deve usar Brasif Gateway Microsoft Graph, nunca SMTP
- Falhas do gateway devem ser registradas sem segredo
- Não deve depender de Redis/Celery

## UX

- Telas operacionais devem funcionar no celular
- Inventário deve ter ações rápidas
- QR Code/lookup deve facilitar campo
- Mensagens devem ser objetivas

## Qualidade

- Testes automatizados devem passar
- Lint deve passar
- Compileall deve passar
- CI deve executar testes, lint, coverage e build Docker
- Migrations devem formar uma cadeia íntegra
- Configuração não deve expor segredos
- Produção deve usar HTTPS e cookies seguros
- Checklist de homologação final deve ser executado
