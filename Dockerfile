# 使用官方的 Docker-in-Docker 镜像作为基础
FROM docker:dind

# 安装 Python 和构建 curl-impersonate 所需的依赖
RUN apk add --no-cache python3 py3-pip curl vim git bash \
    build-base openssl-dev nghttp2-dev zlib-dev linux-headers \
    autoconf automake libtool cmake go ninja perl wget &&  \
    ln -sf python3 /usr/bin/python

# 设置工作目录
WORKDIR /app

# 复制 requirements 文件
COPY ./requirements.lock /app/

# 使用 --break-system-packages 安装依赖
RUN sed '/-e /d' requirements.lock > requirements.txt && \
    pip install --break-system-packages --no-cache-dir --upgrade pip && \
    pip install --break-system-packages --no-cache-dir -r requirements.txt

# 删除不再需要的构建依赖，减小镜像体积
RUN apk del build-base openssl-dev nghttp2-dev linux-headers \
    autoconf automake libtool cmake go ninja perl wget

# 复制源代码
COPY ./src /app/src

# 设置 Python 路径
ENV PYTHONPATH=/app/src
ENV DOCKER_BUILDKIT=1

# 暴露端口
EXPOSE 3333

# 启动脚本
COPY ./docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 设置容器入口点
ENTRYPOINT ["docker-entrypoint.sh"]

# 默认命令
CMD ["python","-m", "omnimcp_be.main"]