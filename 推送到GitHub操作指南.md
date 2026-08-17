# 推送代码到 GitHub 操作指南

> 本文档针对当前办公网络环境（SSH 被封锁，仅 HTTPS 可用）编写。

---

## 前置条件（已配置好，不用重复做）

以下配置已写入 `.gitconfig`，新文件夹无需重新设置：

```ini
[user]
    name = WangZhangyin
    email = wangzhangyin@users.noreply.github.com
[http]
    schannelCheckRevoke = false    # 跳过证书吊销检查（公司网络 CRL 离线）
    sslBackend = openssl           # 用 OpenSSL 替代 Schannel（Schannel 会超时）
```

---

## 推送新文件夹的步骤

### 第 1 步：在 GitHub 网页上创建空仓库

1. 打开 https://github.com/new
2. 填写 Repository name（如 `my-new-project`）
3. 选择 **Private**
4. **不要勾选** "Add a README file"、"Add .gitignore"、"Choose a license"
5. 点击 **Create repository**

### 第 2 步：在本地初始化并推送

打开命令行，执行：

```bash
# 进入你的项目文件夹
cd /d "E:\your\project\folder"

# 初始化 git 仓库
git init

# 添加所有文件（会自动尊重 .gitignore 的规则）
git add .

# 提交
git commit -m "Initial commit"

# 分支改名为 main
git branch -M main

# 添加远程仓库（把 <TOKEN> 换成你的 Personal Access Token）
git remote add origin https://<TOKEN>@github.com/northkd/你的仓库名.git

# 推送
git push -u origin main
```

### 第 3 步：验证

打开 https://github.com/northkd/你的仓库名 看看文件是否都在。

---

## 后续推送（仓库已存在时）

以后每次修改了代码，只需要：

```bash
cd /d "E:\your\project\folder"

# 查看改了什么
git status

# 添加所有改动
git add .

# 提交（写清楚改了什么）
git commit -m "描述你这次的修改"

# 推送
git push
```

---

## Token 说明

### 什么是 Personal Access Token？

GitHub 从 2021 年起不再允许用密码推送代码，必须用 **Personal Access Token（PAT）** 代替密码。你可以把它理解为一个"专属门禁卡"，只对你授权的仓库有效。

### 获取 Token

1. 打开 https://github.com/settings/tokens
2. 点击 **Generate new token** → **Generate new token (classic)**
3. 勾选 `repo`（完整仓库访问权限）
4. 设置过期时间
5. 点击 **Generate token**
6. **立刻复制保存**，页面关了就看不到了

### Token 过期了怎么办？

重新生成一个，然后更新远程地址：

```bash
git remote set-url origin https://新TOKEN@github.com/northkd/仓库名.git
```

---

## .gitignore 模板

每次新建项目时，建议先创建 `.gitignore` 文件，避免推送不需要的东西：

**Python 项目通用模板：**

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/

# 数据文件（按需调整）
data/
*.xlsx
*.csv

# 工具目录
.omo/
.aris/
.codegraph/

# 系统文件
.DS_Store
Thumbs.db

# 密钥和敏感文件（绝对不能推！）
.env
*.pem
*.key
id_ed25519
id_rsa
```

---

## 常见问题

### Q: push 时报 `fatal: detected dubious ownership`

说明文件夹的所有者和当前用户不一致（常见于从别处拷贝的项目）。执行：

```bash
git config --global --add safe.directory "E:/your/project/folder"
```

### Q: push 时报 `remote: Repository not found`

检查仓库名和用户名是否拼写正确。确认仓库确实已创建。

### Q: push 超时

确认 `.gitconfig` 中有这两行（已配置）：

```ini
[http]
    schannelCheckRevoke = false
    sslBackend = openssl
```

### Q: 想推送大数据文件（>100MB）

GitHub 单文件限制 100MB。大文件需要用 Git LFS，或上传到其他平台（如 Google Drive）后在 README 里贴链接。

---

## 安全提醒

| 绝对不要推送                           | 原因                                 |
| -------------------------------------- | ------------------------------------ |
| SSH 私钥（`id_ed25519`、`id_rsa`） | 等于把家门钥匙公开，任何人都能冒充你 |
| `.env` 文件                          | 可能含 API 密钥、数据库密码          |
| Token 本身写进代码                     | 会被 GitHub 自动扫描并告警           |
| 大型数据集                             | 超出 GitHub 限制，且泄露原始数据     |
