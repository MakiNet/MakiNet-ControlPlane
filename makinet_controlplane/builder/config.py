import datetime
import hashlib
import tempfile
import zipfile
from abc import ABC
from pathlib import Path
from typing import Annotated, Any, Generator, Iterable, Literal, Optional, Union

import bson
from loguru import logger
from pydantic import BaseModel, Field, computed_field, field_validator


# 构建配置
class BuildStep(BaseModel, ABC):
    type: str


class CopyStep(BuildStep):
    type: Literal["copy"]  # type: ignore
    src: str
    dest: str


class SetEnvStep(BuildStep):
    type: Literal["setenv"]  # type: ignore
    name: str
    value: str


BuildSteps = Union[CopyStep, SetEnvStep]


class BuildConfig(BaseModel):
    image_slug: str = Field(alias="slug")
    version: str = Field(
        default_factory=lambda: f"{int(datetime.datetime.now(datetime.UTC).timestamp())}"
    )
    steps: list[Annotated[BuildSteps, Field(discriminator="type")]] = []


# 镜像配置
class ImageLayer(BaseModel):
    checksum: dict[
        str, str
    ]  # Path, sha256  # 保留所有文件的 sha256，而非仅 content 中内容
    content: dict[str, bytes]  # Path, content
    deleted_files: list[str] = []

    @computed_field
    @property
    def slug(self) -> str:
        return hashlib.sha256(
            " ".join(self.checksum.values()).encode("utf-8")
        ).hexdigest()

    @field_validator("content", mode="before")
    def validate_content(cls, content: dict[str, bytes]):
        for path, _ in content.items():
            if Path(path).is_absolute():
                raise ValueError("Path must be relative")

        return content

    def pack(self, path: Path, compression: bool):
        """将镜像打包为 Zip 文件

        Args:
            path (Path): Zip 文件路径
            compression (bool): 是否压缩镜像文件

        Note:
            镜像文件结构:
                - info.bson: 镜像信息文件（除 self.content 以外的所有内容）
                - content.bson: 镜像内容文件（self.content 的 BSON 结构，Key 已被转为 str）
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(
            file=path,
            mode="w",
            compression=zipfile.ZIP_STORED if not compression else zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as zip_file:
            zip_file.writestr(
                "info.bson",
                bson.dumps(self.model_dump(mode="json", exclude={"content"})),
            )

            # 防止出现绝对路径，并将 Path 转换为 str
            for file_path, content in self.content.items():
                if Path(file_path).is_absolute():
                    logger.error("Error when packing image: Path must be relative")

            zip_file.writestr("content.bson", bson.dumps(self.content))

    @classmethod
    def unpack(cls, path: Path):
        """从 Zip 文件中解包镜像
        Args:
            path (Path): Zip 文件路径

        Returns:
            ImageLayer: 解包后的镜像
        """
        with zipfile.ZipFile(path, "r") as zip_file:
            info: dict[str, Any] = bson.loads(zip_file.read("info.bson"))  # type: ignore
            content: dict[str, bytes] = bson.loads(zip_file.read("content.bson"))  # type: ignore

        return cls(**info, content=content)


class Image(BaseModel):
    """镜像。

    Note:
        启动时从 .image.env 中加载环境变量
    """

    slug: str
    version: str
    layers: list[ImageLayer]

    def pack(self, path: Path, compression: bool):
        """将镜像打包为 Zip 文件
        Args:
            path (Path): Zip 文件路径
            compression (bool): 是否压缩镜像文件

        Note:
            镜像文件结构:
                - info.bson: 镜像信息文件（除 self.layers 以外的所有内容）
                - layers/: 镜像层文件夹
                    - layer_0.zip: 镜像层 0
                    - layer_1.zip: 镜像层 1
                    - ...
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(
            path,
            "w",
            compression=zipfile.ZIP_STORED if not compression else zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as zip_file:
            zip_file.writestr(
                "info.bson",
                bson.dumps(self.model_dump(mode="json", exclude={"layers"})),
            )

            zip_file.mkdir("layers")
            with tempfile.TemporaryDirectory() as tmpdir:
                for i, layer in enumerate(self.layers):
                    layer.pack(Path(tmpdir) / f"layers/layer_{i}.zip", compression)

                    # 压缩镜像层
                    zip_file.write(
                        Path(tmpdir) / f"layers/layer_{i}.zip",
                        f"layers/layer_{i}.zip",
                    )

    @classmethod
    def unpack(cls, path: Path):
        """从 Zip 文件中解包镜像
        Args:
            path (Path): Zip 文件路径
        Returns:
            Image: 解包后的镜像
        """
        with zipfile.ZipFile(path, "r") as zip_file:
            info: dict[str, Any] = bson.loads(zip_file.read("info.bson"))  # type: ignore
            layers: list[ImageLayer] = []

            for i in range(len(zip_file.namelist())):
                # 该文件不是 layers 文件夹下的文件，继续循环
                if f"layers/layer_{i}.zip" not in zip_file.namelist():
                    continue

                # 解压镜像层
                with tempfile.TemporaryDirectory() as tmp_dir:
                    zip_file.extract(f"layers/layer_{i}.zip", tmp_dir)
                    layers.append(
                        ImageLayer.unpack(Path(tmp_dir) / f"layers/layer_{i}.zip")
                    )

        return cls(**info, layers=layers)

    def extract_to_directory(self, path: Path):
        """将镜像解包到目录中
        Args:
            path (Path): 目录路径
        """
        path.mkdir(parents=True, exist_ok=True)

        for layer in self.layers:
            for file_path, content in layer.content.items():
                (path / file_path).parent.mkdir(parents=True, exist_ok=True)
                (path / file_path).write_bytes(content)

            for deleted_file in layer.deleted_files:
                (path / deleted_file).unlink(missing_ok=True)

    def get_file_list(self) -> list[str]:
        return list(self.layers[-1].checksum.keys())

    def __repr__(self) -> str:
        return f"""Image(
    slug={self.slug},
    version={self.version},
    layers={len(self.layers)},
    files={self.get_file_list()[0:3]}...
)"""
