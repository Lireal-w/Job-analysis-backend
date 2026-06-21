#!/bin/bash
# ============================================================
# fba 项目一键更新脚本
# 用法：
#   chmod +x update.sh && ./update.sh
#
# 功能：
#   初次运行 → git clone + docker compose build + up
#   后续运行 → 对比本地/远程 commit hash → 有更新则 pull + rebuild + restart
# ============================================================

set -e

# ── 配置（按需修改）────────────────────────────────────────
PROJECT_DIR="/opt/fba"
REPO_URL="https://gitee.com/Lireal-W/fastapi-best-architecture.git"
BRANCH="master"
ENV_FILE="deploy/backend/docker-compose/.env.server"

# ── 颜色输出 ───────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err()   { echo -e "${RED}[ERR]${NC} $1"; }

# ── 检测命令依赖 ───────────────────────────────────────────
for cmd in git docker docker compose; do
    if ! command -v "$cmd" &>/dev/null; then
        log_err "缺少依赖: $cmd，请先安装"
        exit 1
    fi
done

# ── 步骤 1: 检查/克隆项目 ──────────────────────────────────
echo ""
log_info "============================================"
log_info "  fba 项目部署更新脚本"
log_info "============================================"
echo ""

if [ ! -d "$PROJECT_DIR/.git" ]; then
    log_info "首次部署，正在克隆项目..."
    mkdir -p "$PROJECT_DIR"
    git clone "$REPO_URL" -b "$BRANCH" "$PROJECT_DIR"
    log_ok "项目克隆完成"
    FIRST_RUN=true
else
    log_info "项目已存在，检查更新..."
    cd "$PROJECT_DIR"
    FIRST_RUN=false
fi

cd "$PROJECT_DIR"

# ── 步骤 2: 对比 commit hash ──────────────────────────────
LOCAL_HASH=$(git rev-parse HEAD 2>/dev/null || echo "none")

log_info "本地版本: ${LOCAL_HASH:0:12}"

# 获取远程最新 commit hash（不拉取代码）
REMOTE_HASH=$(git ls-remote origin "$BRANCH" 2>/dev/null | awk '{print $1}' || echo "none")

if [ "$REMOTE_HASH" = "none" ]; then
    log_warn "无法连接到远程仓库，使用本地代码继续"
elif [ "$LOCAL_HASH" = "$REMOTE_HASH" ] && [ "$FIRST_RUN" = false ]; then
    log_ok "已是最新版本，无需更新"
    # 检查容器是否在运行，没运行则启动
    if ! docker compose ps --status running 2>/dev/null | grep -q "Up"; then
        log_info "容器未运行，正在启动..."
        docker compose up -d
        log_ok "容器已启动"
    else
        log_info "所有容器运行正常"
    fi
    echo ""
    log_info "服务访问地址:"
    echo "  FastAPI:  http://$(curl -s ifconfig.me 2>/dev/null || echo 'localhost'):8001/docs"
    echo "  Grafana:  http://localhost:3000"
    exit 0
fi

# ── 步骤 3: 有更新，拉取最新代码 ───────────────────────────
if [ "$FIRST_RUN" = false ]; then
    log_info "发现新版本: ${REMOTE_HASH:0:12}，正在拉取..."
    git pull origin "$BRANCH"
    log_ok "代码已更新"
fi

# ── 步骤 4: 检查 .env.server 配置文件 ─────────────────────
if [ ! -f "$ENV_FILE" ]; then
    log_warn "配置文件 $ENV_FILE 不存在"
    echo ""
    echo "请先创建配置文件:"
    echo "  mkdir -p $(dirname $ENV_FILE)"
    echo "  cat > $ENV_FILE << 'EOF'"
    echo "  ENVIRONMENT='prod'"
    echo "  DATABASE_TYPE='postgresql'"
    echo "  DATABASE_HOST='127.0.0.1'"
    echo "  DATABASE_PORT=5432"
    echo "  DATABASE_USER='user_QkaGxc'"
    echo "  DATABASE_PASSWORD='password_Wjwws3'"
    echo "  REDIS_HOST='127.0.0.1'"
    echo "  REDIS_PORT=6379"
    echo "  REDIS_PASSWORD='redis_Pe2HaC'"
    echo "  REDIS_DATABASE=0"
    echo "  TOKEN_SECRET_KEY='4v5CtD3Aas3SPqIuqxgb4fryJBMS44xoYAgzybVJD_A'"
    echo "  EOF"
    echo ""
    log_err "请创建配置文件后重新运行脚本"
    exit 1
fi

# ── 步骤 5: 构建并启动 Docker 服务 ─────────────────────────
log_info "正在构建 Docker 镜像..."
docker compose build --pull
log_ok "镜像构建完成"

log_info "正在启动服务..."
docker compose up -d --remove-orphans
log_ok "服务已启动"

# ── 步骤 6: 清理旧镜像 ────────────────────────────────────
docker image prune -f > /dev/null 2>&1

# ── 步骤 7: 保存当前 hash 到文件（备用记录） ──────────────
git rev-parse HEAD > .deploy_hash

# ── 完成 ──────────────────────────────────────────────────
echo ""
log_info "============================================"
log_ok "  部署完成！"
log_info "============================================"
echo ""
log_info "当前版本: $(git rev-parse --short HEAD)"
echo ""

# 显示容器状态
docker compose ps

echo ""
log_info "服务访问地址:"
echo "  FastAPI:  http://$(curl -s ifconfig.me 2>/dev/null || echo 'localhost'):8001/docs"
echo "  Celery Flower: http://localhost:8555"
echo "  Grafana:      http://localhost:3000"
echo ""
log_info "查看实时日志: docker compose logs -f fba_server"
