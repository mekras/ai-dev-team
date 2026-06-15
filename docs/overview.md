# Обзор продукта

<table>
  <tr>
    <td>
      <strong>Ваш проект</strong>
      <table>
        <tr>
          <td style="text-align: center">Исходные коды</td>
        </tr>
        <tr>
          <td style="text-align: center">Проектная документация</td>
        </tr>
        <tr>
          <td style="text-align: center">
            <a href="docs/knowledge.md">Корпус знаний проекта</a>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="text-align: center">
      <strong>ai-dev-team</strong>
      <table>
        <tr>
          <td style="text-align: center">Роли</td>
        </tr>
        <tr>
          <td style="text-align: center">Навыки</td>
        </tr>
        <tr>
          <td style="text-align: center">Корпус знаний ai-dev-team</td>
        </tr>
        <tr>
          <td style="text-align: center">Слой управления применением ИИ</td>
        </tr>
      </table>
    </td>
  </tr>
</table>

## Слой управления применением ИИ

Фундаментом продукта является
[коллекция навыков для управления применением ИИ](https://github.com/mekras/ai-agent-supervisor).

Этот слой обеспечивает системное, безопасное и проверяемое использование ИИ в
проектах. Задача этих навыков — защищать человека и проект от неправильного или
неподходящего применения ИИ.

## Корпус знаний проекта

Подробнее, см. https://github.com/mekras/project-knowlege-corpus.

## Скрытй локальный слой знаний (тайные знания)

Продукт поддерживает локальные знания проекта для агента: `AGENTS.local.md`,
`rules.local/` и похожие неотслеживаемые материалы. Этот слой нужен для
сведений, которые помогают агенту работать точнее, но не должны попадать в VCS.
