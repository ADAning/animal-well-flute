"""自定义异常类"""


class AnimalWellFluteError(Exception):
    """动物井笛子项目基础异常类"""

    pass


class ParseError(AnimalWellFluteError):
    """简谱解析错误"""

    pass


class ConversionError(AnimalWellFluteError):
    """音符转换错误"""

    pass


class PlaybackError(AnimalWellFluteError):
    """播放错误"""

    pass


class ConfigError(AnimalWellFluteError):
    """配置错误"""

    pass


class SongNotFoundError(AnimalWellFluteError):
    """乐曲未找到错误"""

    pass
