"""新的音符转换器 - 使用自适应映射系统"""

from typing import List, Union, Optional
from ..data.music_theory import RelativeNote, PhysicalNote, MappingStrategy
from ..core.mapping import AdaptiveMapper, MappingOptimizer
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AutoConverter:
    """自动音符转换器"""

    def __init__(self):
        self.mapper = AdaptiveMapper()
        self.optimizer = MappingOptimizer()
        logger.info("AutoConverter initialized")

    def convert_jianpu(
        self,
        parsed_jianpu: List[List[RelativeNote]],
        strategy: Union[str, MappingStrategy] = "optimal",
        manual_offset: Optional[float] = None,
        auto_preference: Optional[str] = None,
    ) -> List[List[PhysicalNote]]:
        """
        转换简谱到物理音高

        Args:
            parsed_jianpu: 解析后的相对音高简谱
            strategy: 映射策略 ("optimal", "high", "low", "auto", "manual")
            manual_offset: 手动偏移量（当strategy为"manual"时使用）
            auto_preference: 自动策略的偏好 ("optimal", "high", "low")

        Returns:
            物理音符列表
        """
        logger.info(
            f"Converting jianpu with {len(parsed_jianpu)} bars using {strategy} strategy"
        )

        # 展平所有音符
        all_relative_notes = []
        for bar in parsed_jianpu:
            all_relative_notes.extend(bar)

        # 转换策略
        if isinstance(strategy, str):
            if strategy == "auto":
                # 自动选择最佳策略，考虑用户偏好
                if auto_preference:
                    physical_notes, used_strategy = (
                        self.optimizer.find_best_mapping_with_preference(
                            all_relative_notes, auto_preference
                        )
                    )
                else:
                    physical_notes, used_strategy = self.optimizer.find_best_mapping(
                        all_relative_notes
                    )
                logger.info(f"Auto-selected strategy: {used_strategy}")
            elif strategy == "manual":
                if manual_offset is None:
                    raise ValueError(
                        "manual_offset is required when using manual strategy"
                    )
                physical_notes = self.mapper.map_song_to_flute(
                    all_relative_notes, MappingStrategy.MANUAL, manual_offset
                )
            else:
                # 字符串策略转换
                strategy_map = {
                    "optimal": MappingStrategy.OPTIMAL,
                    "high": MappingStrategy.HIGH,
                    "low": MappingStrategy.LOW,
                }
                if strategy not in strategy_map:
                    raise ValueError(f"Unknown strategy: {strategy}")

                physical_notes = self.mapper.map_song_to_flute(
                    all_relative_notes, strategy_map[strategy], None
                )
        else:
            # 直接使用MappingStrategy枚举
            physical_notes = self.mapper.map_song_to_flute(
                all_relative_notes, strategy, manual_offset
            )

        # 重新组织为小节结构
        converted_jianpu = []
        note_index = 0

        for bar in parsed_jianpu:
            converted_bar = []
            for _ in bar:
                converted_bar.append(physical_notes[note_index])
                note_index += 1
            converted_jianpu.append(converted_bar)

        self._log_conversion_summary(converted_jianpu)
        return converted_jianpu

    def get_conversion_preview(self, parsed_jianpu: List[List[RelativeNote]]) -> dict:
        """获取转换预览信息"""
        all_relative_notes = []
        for bar in parsed_jianpu:
            all_relative_notes.extend(bar)

        # 获取映射建议
        suggestions = self.mapper.get_mapping_suggestions(all_relative_notes)

        # 添加转换预览
        preview = {
            "suggestions": suggestions,
            "bar_count": len(parsed_jianpu),
            "total_notes": len(all_relative_notes),
        }

        return preview

    def _log_conversion_summary(
        self, converted_jianpu: List[List[PhysicalNote]]
    ) -> None:
        """记录转换摘要"""
        total_notes = sum(len(bar) for bar in converted_jianpu)

        # 统计物理音高范围
        all_heights = []
        for bar in converted_jianpu:
            for note in bar:
                if note.physical_height is not None:
                    all_heights.append(note.physical_height)

        if all_heights:
            min_height = min(all_heights)
            max_height = max(all_heights)
            span = max_height - min_height

            logger.info(f"Conversion summary:")
            logger.info(f"  Total notes: {total_notes}")
            logger.info(f"  Physical range: {min_height:.1f} to {max_height:.1f}")
            logger.info(f"  Span: {span:.1f} semitones ({span/12:.1f} octaves)")

        logger.info(f"Successfully converted {len(converted_jianpu)} bars")
