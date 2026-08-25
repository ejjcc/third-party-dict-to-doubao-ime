# 第三方输入法词库导入豆包输入法（macOS）

这个工具将第三方输入法的用户词库导入当前豆包输入法账号。目前支持微信输入法（WeType）本地词库和搜狗 `SGPU` 备份，后续可通过新增来源适配器继续扩展。

它同时是一个遵循开放 [Agent Skills 规范](https://agentskills.io/specification) 的可移植 Skill，不绑定某一家 Agent 产品。Claude Code、Codex、GitHub Copilot，以及其他兼容 `SKILL.md` 的 Agent 都可以使用同一份目录。

## 安装 Agent Skill

克隆仓库后，把整个目录放进所用 Agent 的个人或项目 Skill 目录。下面任选一个，不需要重复安装：

### Claude Code

```bash
git clone https://github.com/ejjcc/third-party-dict-to-doubao-ime.git \
  ~/.claude/skills/third-party-dict-to-doubao-ime
```

Claude Code 也支持放入项目级 `.claude/skills/third-party-dict-to-doubao-ime/`。

### Codex

```bash
git clone https://github.com/ejjcc/third-party-dict-to-doubao-ime.git \
  ~/.codex/skills/third-party-dict-to-doubao-ime
```

### GitHub Copilot

```bash
git clone https://github.com/ejjcc/third-party-dict-to-doubao-ime.git \
  ~/.copilot/skills/third-party-dict-to-doubao-ime
```

项目级安装可放入 `.github/skills/` 或通用的 `.agents/skills/`。其他 Agent 请将仓库放入该产品支持的 Skill 目录。

安装后直接用自然语言即可，例如：

```text
识别我本机受支持的第三方输入法词库，先 dry-run，再安全导入豆包输入法。
```

支持显式调用的客户端也可以使用各自语法，例如 Claude Code 和 GitHub Copilot 的 `/third-party-dict-to-doubao-ime`。是否自动触发则由客户端根据 `SKILL.md` 的描述决定。

## 结论与兼容性

- 已在本机 **WeType 2.2.3** 上完成真实只读演练。
- 微信输入法没有公开的通用词库导出接口；本工具读取其本地 `userDict/v5` LevelDB。
- 读取器由 Python 标准库实现，不会用 LevelDB 打开、恢复或写入微信输入法原库。
- WeType 的存储格式属于内部实现。升级微信输入法后，应先重新执行 `--dry-run` 验证。
- 豆包侧通过其 macOS 输入法内置引擎写入用户词库，同样依赖当前应用内部接口。

## 先做只读演练

```bash
python3 import_user_dict_to_doubao_ime.py --wetype-user-dict --dry-run
```

工具会自动定位：

```text
~/Library/Application Support/WeType/userDict/v5
```

也可以显式指定 `v5` 根目录或其中包含 `CURRENT` 的 LevelDB 目录：

```bash
python3 import_user_dict_to_doubao_ime.py \
  --wetype-user-dict "/path/to/userDict/v5" \
  --dry-run
```

演练只打印文件数、记录数和清洗计数，不打印个人词条。

## 正式导入

确认 dry-run 结果后执行：

```bash
python3 import_user_dict_to_doubao_ime.py --wetype-user-dict
```

正式导入会：

1. 短暂停止微信输入法，复制一致性快照，然后立即重新启动微信输入法。
2. 清洗并去重用户词条。
3. 在运行目录中备份当前豆包用户词库。
4. 停止豆包输入法，批量写入词条，并在结束或异常时重新启动豆包输入法。
5. 抽样验证写入结果，并保留导入与验证日志。

默认是增量学习，不会主动清空豆包已有词库。首次试用可限制导入数量：

```bash
python3 import_user_dict_to_doubao_ime.py --wetype-user-dict --limit 100
```

对微信输入法来源，`--limit` 优先选择序列号较新的词条。

## 数据与安全

- 微信输入法源目录只读；所有解析都在复制出的快照上进行。
- 每次运行创建 `doubao-user-dict-import-时间戳/`，目录权限为 `0700`。
- `import.tsv`、`verify.tsv` 包含个人词条，权限为 `0600`，并已加入 `.gitignore`。
- 正式导入前的豆包备份位于运行目录的 `backup-before-import/`。
- `--no-stop-wetype` 会在 WeType 运行时复制数据库，可能得到不一致快照，只建议诊断时使用。

## 搜狗来源与其他参数

搜狗备份（需要 `pypinyin`）：

```bash
python3 -m pip install pypinyin
python3 import_user_dict_to_doubao_ime.py /path/to/sogou-backup.bin --dry-run
```

查看完整参数：

```bash
python3 import_user_dict_to_doubao_ime.py --help
```

正式写入还要求已安装豆包输入法，并可使用 `clang`（Xcode Command Line Tools）。

## 开发与测试

```bash
python3 -m unittest discover -s tests -v
uvx --from skills-ref agentskills validate /path/to/third-party-dict-to-doubao-ime
```

本项目采用 [MIT License](LICENSE)。欢迎提交兼容性报告和改进，但请勿在 issue、日志或测试数据中上传真实个人词库。
