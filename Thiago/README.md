# Explicação do porque o do aluno (Thiago) não estar no docker!

Devido à necessidade de interação humana para resolver o CAPTCHA imposto pelo site após o início do desenvolvimento, não foi possível rodar o crawler dentro de um container Docker de forma totalmente automatizada. Isso porque:

## Resolução de CAPTCHA: O modo headless não permite a visualização e intervenção na resolução dos CAPTCHAs.

## Interação Manual Necessária: O usuário precisa verificar e resolver o CAPTCHA manualmente para prosseguir com a coleta dos dados.

Mesmo com essa limitação na automatização por meio do Docker, todos os resultados obtidos antes da implementação do CAPTCHA estão disponíveis. Assim, os dados coletados anteriormente podem ser utilizados para análises ou integrações subsequentes.