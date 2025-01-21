import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import toml
from loguru import logger

from .config import (
    BuildConfig,
    BuildStep,
    BuildSteps,
    CopyStep,
    Image,
    ImageLayer,
    SetEnvStep,
)


def evaluate_build_step(
    step: BuildStep, source_path: Path, build_temp_path: Path
) -> None:
    """执行某个构建步骤

    Args:
        step (BuildStep): 步骤信息
        source_path (Path): 源代码路径（即构建配置文件所在的文件夹）
        artifact_path (Path): 构建使用的临时文件夹

    Returns:
        ImageLayer: _description_
    """
    # 执行
    if isinstance(step, CopyStep):
        # shutil.copytree(source_path / step.src, build_temp_path / step.dest)a
        for file in source_path.rglob(step.src):
            # 跳过文件夹
            if file.is_dir():
                continue

            # 跳过 .image.zip 文件
            if file.name.endswith('.image.zip'):
                logger.warning(f"Skip {file} because it is a .image.zip file")
                continue

            dst = build_temp_path / file.relative_to(source_path)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(file, dst)
    elif isinstance(step, SetEnvStep):
        envfile = build_temp_path / ".image.env"
        envfile.touch(exist_ok=True)

        fd = envfile.open("a")
        fd.write(f"\n{step.name}={step.value}")
        fd.close()


def generate_image_layer(build_temp_path: Path) -> ImageLayer:
    """从临时文件夹中生成镜像层

    Args:
        build_temp_path (Path): 临时文件夹路径

    Returns:
        ImageLayer: 生成的镜像层
    """
    # 计算 checksum
    content: dict[str, bytes] = {}
    checksum: dict[str, str] = {}

    for path in build_temp_path.rglob("*"):
        if path.is_dir():
            continue

        rpath = path.relative_to(build_temp_path)
        content[rpath.as_posix()] = path.read_bytes()
        checksum[rpath.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()

    return ImageLayer(
        content=content,
        checksum=checksum,
    )


def build_image_from_directory(path: Path) -> Image:
    """从目录中构建镜像，暂不支持分层

    Args:
        path (Path): 目录路径

    Returns:
        Image: 构建后的镜像
    """
    # 加载配置
    config = BuildConfig.model_validate(toml.load(path / "maki-build.toml"))

    # 构建镜像
    image = Image(slug=config.image_slug, version=config.version, layers=[])

    # TODO: 镜像分层
    with tempfile.TemporaryDirectory() as build_temp_path:
        for step in config.steps:
            evaluate_build_step(step, path, Path(build_temp_path))

        image.layers.append(generate_image_layer(Path(build_temp_path)))

    return image


def save_image(image: Image, path: Path, compression: bool = False) -> None:
    """保存镜像
    Args:
        image (Image): 镜像
        path (Path): 保存路径
        compression (bool): 是否压缩
    """
    image.pack(path, compression)


def load_image(path: Path) -> Image:
    """加载镜像
    Args:
        path (Path): 镜像路径
    Returns:
        Image: 镜像
    """
    return Image.unpack(path)


__all__ = [
    "BuildConfig",
    "BuildSteps",
    "Image",
    "ImageLayer",
]
