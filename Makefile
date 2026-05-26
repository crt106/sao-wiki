.PHONY: help setup serve serve-full build deploy clean

VENV       := .venv
PYTHON     := $(VENV)/bin/python
MKDOCS     := $(VENV)/bin/mkdocs
PIP        := $(VENV)/bin/pip
HOST       := 127.0.0.1
PORT       := 8000

DEPS := mkdocs-material \
        mkdocs-awesome-pages-plugin \
        mkdocs-glightbox \
        mkdocs-git-revision-date-localized-plugin \
        mkdocs-git-authors-plugin \
        jieba

help:
	@echo "刀剑物语 Wiki - Makefile 命令"
	@echo ""
	@echo "  make setup       初始化虚拟环境并安装依赖"
	@echo "  make serve       本地开发服务器（快模式，无 Git 元信息）"
	@echo "  make serve-full  本地开发服务器（完整模式，含 Git 元信息）"
	@echo "  make build       生产构建（--strict）"
	@echo "  make deploy      部署到 GitHub Pages"
	@echo "  make clean       清理构建产物"
	@echo "  make deps        仅安装/更新依赖"

setup: $(VENV)/bin/activate
	$(PIP) install --upgrade pip
	$(PIP) install $(DEPS)
	@echo "✓ 环境初始化完成，运行 make serve 启动开发服务器"

$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	@echo "✓ 虚拟环境已创建"

deps:
	$(PIP) install --upgrade $(DEPS)

serve: $(VENV)/bin/activate
	MKDOCS_ENABLE_GIT_META=false \
	WATCHFILES_FORCE_POLLING=true \
	$(MKDOCS) serve --dirtyreload -a $(HOST):$(PORT)

serve-full: $(VENV)/bin/activate
	$(MKDOCS) serve -a $(HOST):$(PORT)

build: $(VENV)/bin/activate
	$(MKDOCS) build --strict

deploy: $(VENV)/bin/activate
	$(MKDOCS) gh-deploy --force

clean:
	rm -rf site/
	rm -rf .cache/
	@echo "✓ 已清理 site/ 和 .cache/"
