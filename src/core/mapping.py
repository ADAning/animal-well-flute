"""自适应音域映射系统 - 将相对音高映射到物理音高"""

from typing import List, Optional, Tuple
import math
from ..data.music_theory import (
    RelativeNote, PhysicalNote, RangeInfo, MappingStrategy,
    MusicNotation, FlutePhysical, RangeAnalyzer
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AdaptiveMapper:
    """自适应音域映射器"""
    
    def __init__(self):
        self.flute = FlutePhysical()
        self.analyzer = RangeAnalyzer()
        logger.info("AdaptiveMapper initialized")
    
    def map_song_to_flute(
        self, 
        relative_notes: List[RelativeNote],
        strategy: MappingStrategy = MappingStrategy.OPTIMAL,
        manual_offset: Optional[float] = None,
    ) -> List[PhysicalNote]:
        """
        将相对音高映射到笛子物理音高
        
        Args:
            relative_notes: 相对音符列表
            strategy: 映射策略
            manual_offset: 手动偏移量（当strategy为MANUAL时使用）
            
        Returns:
            物理音符列表
            
        Raises:
            ValueError: 音域超出笛子能力范围
        """
        # 1. 分析相对音域
        range_info = self.analyzer.analyze_relative_notes(relative_notes)
        logger.info(f"Song range: {range_info.min_height:.1f} to {range_info.max_height:.1f} "
                   f"(span: {range_info.span:.1f} semitones, {range_info.octaves:.1f} octaves)")
        
        # 2. 验证音域可行性
        if range_info.span > 24:  # 2个八度
            raise ValueError(f"Song range ({range_info.span:.1f} semitones) exceeds 2 octaves limit")
        
        if range_info.span > self.flute.PHYSICAL_RANGE:
            raise ValueError(f"Song range ({range_info.span:.1f} semitones) exceeds flute physical range "
                           f"({self.flute.PHYSICAL_RANGE:.1f} semitones)")
        
        # 3. 计算映射偏移
        if strategy == MappingStrategy.MANUAL and manual_offset is not None:
            offset = manual_offset
        else:
            offset = self._calculate_optimal_offset(range_info, strategy)
        
        logger.info(f"Calculated mapping offset: {offset:.1f} semitones")
        
        # 4. 执行映射
        physical_notes = []
        for note in relative_notes:
            physical_note = self._map_single_note(note, offset)
            physical_notes.append(physical_note)
        
        # 5. 验证最终结果
        self._validate_final_mapping(physical_notes)
        
        logger.info(f"Successfully mapped {len(physical_notes)} notes to physical range")
        return physical_notes
    
    def _calculate_optimal_offset(
        self, 
        range_info: RangeInfo, 
        strategy: MappingStrategy
    ) -> float:
        """计算最优映射偏移量"""
        logger.info(f"Calculating optimal offset for {strategy.value} strategy")
        logger.info(f"Range info: {range_info.min_height:.1f} to {range_info.max_height:.1f}")
        logger.info(f"Flute range: {self.flute.MIN_PHYSICAL_HEIGHT:.1f} to {self.flute.MAX_PHYSICAL_HEIGHT:.1f}")
        logger.info(f"Strategy: {strategy.value}")

        if strategy == MappingStrategy.OPTIMAL:
            # 居中策略：让乐曲音域在笛子音域中居中
            song_center = (range_info.min_height + range_info.max_height) / 2
            flute_center = (self.flute.MIN_PHYSICAL_HEIGHT + self.flute.MAX_PHYSICAL_HEIGHT) / 2
            offset = flute_center - song_center
            # 将offset归到0.5的整数倍, 以适配半音, 向上半音取整
            offset = math.ceil(offset * 2) / 2
            logger.info(f"Optimal offset calculated: {offset:.1f} semitones")

        elif strategy == MappingStrategy.HIGH:
            # 高音策略：让最高音接近笛子最高音
            offset = self.flute.MAX_PHYSICAL_HEIGHT - range_info.max_height
            
        elif strategy == MappingStrategy.LOW:
            # 低音策略：让最低音接近笛子最低音
            offset = self.flute.MIN_PHYSICAL_HEIGHT - range_info.min_height
            
        else:
            offset = 0.0
            
        logger.info(f"Offset calculated: {offset:.1f} semitones")

        # 确保映射后的音域在笛子范围内
        mapped_min = range_info.min_height + offset
        mapped_max = range_info.max_height + offset
        logger.info(f"Mapped range: {mapped_min:.1f} to {mapped_max:.1f}")
        
        # 如果初始偏移超出范围，调整到合适的位置
        if mapped_min < self.flute.MIN_PHYSICAL_HEIGHT:
            # 最低音超出下限，向上调整
            offset = self.flute.MIN_PHYSICAL_HEIGHT - range_info.min_height
        elif mapped_max > self.flute.MAX_PHYSICAL_HEIGHT:
            # 最高音超出上限，向下调整
            offset = self.flute.MAX_PHYSICAL_HEIGHT - range_info.max_height
        
        logger.info(f"Final offset: {offset:.1f} semitones")
        return offset
    
    def _map_single_note(self, relative_note: RelativeNote, offset: float) -> PhysicalNote:
        """映射单个音符"""
        if relative_note.relative_height is None:
            # 休止符
            physical_height = None
        else:
            physical_height = relative_note.relative_height + offset
        
        # 获取按键组合
        key_combination = self.flute.get_key_combination(physical_height)
        
        return PhysicalNote(
            notation=relative_note.notation,
            physical_height=physical_height,
            time_factor=relative_note.time_factor,
            key_combination=key_combination
        )
    
    def _validate_final_mapping(self, physical_notes: List[PhysicalNote]) -> None:
        """验证最终映射结果"""
        invalid_notes = []
        
        for i, note in enumerate(physical_notes):
            if not self.flute.is_playable(note.physical_height):
                invalid_notes.append((i, note))
        
        if invalid_notes:
            error_msg = f"Found {len(invalid_notes)} unplayable notes after mapping:\n"
            for i, note in invalid_notes[:5]:  # 只显示前5个
                error_msg += f"  Note {i}: {note.notation} -> {note.physical_height:.1f}\n"
            if len(invalid_notes) > 5:
                error_msg += f"  ... and {len(invalid_notes) - 5} more"
            raise ValueError(error_msg.strip())
        
        # 验证音域范围
        range_info = self.analyzer.analyze_physical_notes(physical_notes)
        if not self.flute.validate_range(range_info.min_height, range_info.max_height):
            raise ValueError(f"Final mapped range ({range_info.min_height:.1f} to "
                           f"{range_info.max_height:.1f}) exceeds flute capabilities")
    
    def get_mapping_suggestions(self, relative_notes: List[RelativeNote]) -> dict:
        """获取映射建议"""
        range_info = self.analyzer.analyze_relative_notes(relative_notes)
        
        suggestions = {}
        
        # 尝试不同策略
        for strategy in [MappingStrategy.OPTIMAL, MappingStrategy.HIGH, MappingStrategy.LOW]:
            try:
                offset = self._calculate_optimal_offset(range_info, strategy)
                mapped_min = range_info.min_height + offset
                mapped_max = range_info.max_height + offset
                
                suggestions[strategy.value] = {
                    "offset": offset,
                    "mapped_range": (mapped_min, mapped_max),
                    "feasible": self.flute.validate_range(mapped_min, mapped_max)
                }
            except Exception as e:
                suggestions[strategy.value] = {
                    "error": str(e),
                    "feasible": False
                }
        
        # 音域统计
        suggestions["analysis"] = {
            "original_range": (range_info.min_height, range_info.max_height),
            "span_semitones": range_info.span,
            "span_octaves": range_info.octaves,
            "note_count": range_info.note_count,
            "exceeds_2_octaves": range_info.span > 24,
            "exceeds_flute_range": range_info.span > self.flute.PHYSICAL_RANGE
        }
        
        return suggestions


class MappingOptimizer:
    """映射优化器 - 提供高级映射优化功能"""
    
    def __init__(self):
        self.mapper = AdaptiveMapper()
    
    def find_best_mapping(self, relative_notes: List[RelativeNote]) -> Tuple[List[PhysicalNote], str]:
        """
        找到最佳映射方案
        
        Returns:
            (物理音符列表, 使用的策略名称)
        """
        strategies = [
            MappingStrategy.OPTIMAL,
            MappingStrategy.HIGH, 
            MappingStrategy.LOW
        ]
        
        best_mapping = None
        best_strategy = None
        best_score = float('-inf')
        
        for strategy in strategies:
            try:
                mapping = self.mapper.map_song_to_flute(relative_notes, strategy)
                score = self._evaluate_mapping(mapping)
                
                if score > best_score:
                    best_score = score
                    best_mapping = mapping
                    best_strategy = strategy.value
                    
            except ValueError:
                continue  # 这个策略不可行
        
        if best_mapping is None:
            raise ValueError("No feasible mapping strategy found")
        
        return best_mapping, best_strategy
    
    def find_best_mapping_with_preference(
        self, 
        relative_notes: List[RelativeNote], 
        preference: str
    ) -> Tuple[List[PhysicalNote], str]:
        """
        找到最佳映射方案，优先考虑用户偏好
        
        Args:
            relative_notes: 相对音符列表
            preference: 偏好策略 ("optimal", "high", "low")
            
        Returns:
            (物理音符列表, 使用的策略名称)
        """
        # 策略优先级：首先尝试用户偏好，然后尝试其他策略
        preference_map = {
            "optimal": MappingStrategy.OPTIMAL,
            "high": MappingStrategy.HIGH,
            "low": MappingStrategy.LOW
        }
        
        if preference not in preference_map:
            # 如果偏好无效，回退到普通的最佳映射
            return self.find_best_mapping(relative_notes)
        
        preferred_strategy = preference_map[preference]
        other_strategies = [s for s in [MappingStrategy.OPTIMAL, MappingStrategy.HIGH, MappingStrategy.LOW] 
                          if s != preferred_strategy]
        
        # 首先尝试偏好策略
        try:
            mapping = self.mapper.map_song_to_flute(relative_notes, preferred_strategy)
            return mapping, preferred_strategy.value
        except ValueError:
            # 偏好策略失败，尝试其他策略
            pass
        
        # 尝试其他策略
        for strategy in other_strategies:
            try:
                mapping = self.mapper.map_song_to_flute(relative_notes, strategy)
                return mapping, strategy.value
            except ValueError:
                continue
        
        # 所有策略都失败
        raise ValueError("No feasible mapping strategy found")
    
    def _evaluate_mapping(self, physical_notes: List[PhysicalNote]) -> float:
        """评估映射质量"""
        range_info = self.mapper.analyzer.analyze_physical_notes(physical_notes)
        
        # 评估指标：
        # 1. 音域利用率 (更好地利用笛子音域)
        utilization = range_info.span / self.mapper.flute.PHYSICAL_RANGE
        
        # 2. 居中程度 (居中的映射通常更好)
        center = (range_info.min_height + range_info.max_height) / 2
        flute_center = (self.mapper.flute.MIN_PHYSICAL_HEIGHT + self.mapper.flute.MAX_PHYSICAL_HEIGHT) / 2
        centering = 1.0 - abs(center - flute_center) / (self.mapper.flute.PHYSICAL_RANGE / 2)
        
        # 3. 边界安全性 (避免接近边界)
        min_margin = (range_info.min_height - self.mapper.flute.MIN_PHYSICAL_HEIGHT) / self.mapper.flute.PHYSICAL_RANGE
        max_margin = (self.mapper.flute.MAX_PHYSICAL_HEIGHT - range_info.max_height) / self.mapper.flute.PHYSICAL_RANGE
        safety = min(min_margin, max_margin)
        
        # 综合评分
        score = utilization * 0.3 + centering * 0.4 + safety * 0.3
        return score