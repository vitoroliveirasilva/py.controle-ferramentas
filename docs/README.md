# Documentação do Sistema de Controle de Ferramentas

Este diretório concentra a documentação técnica, operacional e de homologação do projeto.

## Índice recomendado de leitura

1. [Visão geral](00-visao-geral.md)
2. [Instalação local](01-instalacao-local.md)
3. [Execução com Docker](02-docker.md)
4. [Configuração Microsoft Entra ID](03-configuracao-microsoft-entra-id.md)
5. [Variáveis de ambiente](04-variaveis-ambiente.md)
6. [Migrations e banco de dados](05-migrations-e-banco.md)
7. [Testes e qualidade](06-testes-e-qualidade.md)
8. [Deploy e operação](07-deploy.md)
9. [Matriz de permissões](08-matriz-de-permissoes.md)
10. [Guia operacional](09-guia-operacional.md)
11. [Documentação dos módulos](10-modulos.md)
12. [Critérios de aceite](11-criterios-de-aceite.md)
13. [Troubleshooting](12-troubleshooting.md)
14. [Revisão de segurança](13-revisao-de-seguranca.md)
15. [Homologação final](14-homologacao-final.md)
16. [Plano de produção](15-plano-producao.md)

## Estado do MVP

O MVP implementa:

- autenticação Microsoft com autorização local no banco;
- usuários locais, perfis, permissões e escopos;
- cadastros administrativos;
- ferramentas, categorias e locais;
- custódia e linha do tempo;
- transferências com aceite;
- inventário base, divergências e finalização com assinatura;
- ocorrências operacionais e patrimoniais;
- assinaturas internas;
- relatórios e exportações;
- dashboard;
- notificações internas sem Redis;
- configuração para e-mail via Brasif Gateway Microsoft Graph, sem SMTP;
- CI com lint, testes, coverage e build Docker;
- checklist final de homologação e plano de produção;
- UX mobile, evidências, foto de referência e QR Code.

## Convenções

- O Azure/Entra ID autentica.
- O BD autoriza.
- Permissões são verificadas no backend.
- Ações críticas devem gerar auditoria, assinatura ou linha do tempo, conforme o módulo.
- Exclusão física deve ser evitada em dados operacionais e históricos.
