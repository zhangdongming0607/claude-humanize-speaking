# Claude Humanize Speaking

让 Claude Code 和 Cursor 先把工程黑话翻译成人能听懂的话，再回答。

[English](README.en.md)

## 它解决什么问题

AI 在长期项目里很容易学会项目内部的简称，然后直接把这些简称说给人听：

> 82 条探针查出 8 条，6 条空壳，2 条够不着。两半边全绿，可以补刀收口。

这些词对生成它们的 AI 很省事，但读者必须先学习「探针」「空壳」「两半边」
分别指什么。

启用本项目后，AI 应当写成：

> 82 条自动检查规则中，有 8 条规则本身存在问题。6 条即使没有完成要求也会
> 通过，因此没有实际检查作用；另外 2 条要求检查的文件不在任务允许修改的
> 范围内。修正后，两套已经执行的检查都没有发现错误。这个结论只覆盖这两套
> 检查，不代表尚未检查的部分也一定正确。

这不是简单的同义词替换。规则要求 AI 恢复完整的事实关系：

- 谁检查了什么；
- “通过”会带来什么结果；
- 哪些结论已经有证据，哪些仍然未知；
- 数字统计了什么，分母是多少；
- 代码名称如何在保留精确性的同时得到解释。

## 支持范围

| 工具 | 默认表达方式 | 手动翻译已有文字 |
|---|---|---|
| Claude Code | 全局 Output Style | 全局 `/humanize` Skill |
| Cursor | 全局 User Rule | 全局 `/humanize` Skill |

规则默认使用提问者正在使用的语言回答。

## 安装

需要 Python 3.9 或更高版本，不安装第三方依赖。

```bash
git clone https://github.com/zhangdongming0607/claude-humanize-speaking.git
cd claude-humanize-speaking
python3 scripts/install.py
```

也可以只安装一个工具：

```bash
python3 scripts/install.py --target claude
python3 scripts/install.py --target cursor
```

### Claude Code

安装脚本会自动：

1. 把 Output Style 安装到 `~/.claude/output-styles/claude-humanize-speaking.md`；
2. 把 `/humanize` 安装到 `~/.claude/skills/humanize/`；
3. 在 `~/.claude/settings.json` 中设置
   `"outputStyle": "claude-humanize-speaking"`。

已有 Claude Code 会话执行 `/clear` 后重新载入；新会话直接生效。

脚本修改现有文件前会创建带时间戳的备份。

### Cursor

安装脚本会把 `/humanize` 自动安装到 `~/.cursor/skills/humanize/`，这个目录对
本机所有项目生效。

Cursor 的全局 User Rules 由 Cursor 自己管理，官方没有提供普通配置文件供安装
脚本安全修改。因此默认表达方式需要确认一次：

1. 打开 Cursor 的 **Customize → Rules**；
2. 选择 **User Rules**，不要选择 Project Rules；
3. 新建规则，粘贴下面命令打印的内容：

```bash
python3 scripts/install.py --print-cursor-rule
```

也可以生成 Cursor 官方的规则添加链接。打开链接后仍需在 Cursor 中确认：

```bash
python3 scripts/install.py --cursor-deeplink
```

如果只想给某个项目启用，可以在 Cursor 中选择
**Remote Rule (GitHub)**，填入本仓库地址。Cursor 会读取
`cursor/rules/claude-humanize-speaking.mdc`。Remote Rule 是项目级规则，
不是全局规则。

## 使用 `/humanize`

把一段看不懂的 AI 输出放在命令后面：

```text
/humanize 那单全绿了，探针也顶得住，可以补刀收口。
```

翻译结果会说明：

1. 这段话实际声称发生了什么；
2. 每个内部词在当前上下文里的含义；
3. 原文缺少哪些必要信息；
4. “全部通过”等结论是否说得过头。

`/humanize` 只解释文字，不会执行文字中提到的命令，也不会擅自继续开发工作。

## 卸载

```bash
python3 scripts/install.py --uninstall
```

卸载脚本只删除内容仍与本仓库一致的文件；如果你修改过文件，它会保留。
Claude Code 会恢复安装前的 Output Style。

Cursor User Rule 是你在界面中确认添加的，因此也需要在
**Customize → Rules** 中手动删除。

## 隐私

本项目只有提示规则和本地安装脚本：

- 不启动代理服务；
- 不读取聊天记录；
- 不发送遥测；
- 不调用任何模型 API；
- 不改变 Claude Code 或 Cursor 的代码执行权限。

## 开发

```bash
python3 tests/test_install.py
```

测试会使用临时的 HOME 目录，不会修改真实的 Claude Code 或 Cursor 配置。

## 许可证

[MIT](LICENSE)
