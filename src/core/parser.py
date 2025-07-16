"""新的简谱解析器 - 使用相对音高系统"""

from typing import List, Union, Any
from ..data.music_theory import RelativeNote, MusicNotation
from ..utils.logger import get_logger

logger = get_logger(__name__)


class RelativeParser:
    """相对音高简谱解析器"""
    
    def __init__(self):
        self.notation = MusicNotation()
        logger.info("RelativeParser initialized with relative pitch system")
    
    @staticmethod
    def validate_bar(bar: List[RelativeNote], expected_duration: float) -> bool:
        """验证小节的时值是否正确"""
        total_time = sum(note.time_factor for note in bar)
        return abs(total_time - expected_duration) < 1e-6
    
    @staticmethod
    def is_sequence(item: Any) -> bool:
        """检查是否为序列类型 (list 或 tuple)"""
        return isinstance(item, (list, tuple))
    
    def parse_recursively(
        self,
        elements: Any,
        result: List[RelativeNote],
        time_factor: float = 1.0,
        major_offset: float = 0.0,
    ) -> None:
        """递归解析简谱元素到相对音高"""
        
        if not self.is_sequence(elements):
            # 单个音符
            note_time_factor = time_factor
            
            # 处理附点音符 (以'd'结尾)
            if isinstance(elements, str) and elements.endswith("d"):
                note_time_factor *= 1.5
            
            elem = elements
            
            # 处理不同类型的输入
            if isinstance(elem, (int, float)):
                if elem % 0.5 != 0:
                    raise ValueError(f"Invalid note value: {elem}")
                note_str = str(elem)
            elif isinstance(elem, str):
                elem = elem.strip()
                if len(elem) == 1:
                    if elem not in "12345670-":
                        raise ValueError(f"Invalid note character: {elem}")
                    note_str = elem
                    if elem == "-":
                        # 延长音，将时值加到前一个音符
                        if result:
                            result[-1].time_factor += note_time_factor
                            logger.debug(f"Extended previous note by {note_time_factor}")
                        return
                else:
                    note_str = elem.replace("d", "")
            else:
                raise ValueError(f"Unsupported note type: {type(elem)}")
            
            # 获取相对音高
            if note_str == "0":
                relative_height = None  # 休止符
            else:
                base_height = self.notation.get_relative_height(note_str)
                if base_height is None:
                    raise ValueError(f"Unknown note: {note_str}")
                relative_height = base_height + major_offset
            
            # 创建相对音符对象
            note = RelativeNote(
                notation=note_str,
                relative_height=relative_height,
                time_factor=note_time_factor,
            )
            result.append(note)
            logger.debug(f"Parsed relative note: {note_str} "
                        f"(height={relative_height}, time={note_time_factor})")
            return
        
        # 递归处理序列
        for elem in elements:
            self.parse_recursively(
                elem, 
                result, 
                time_factor=time_factor / 2, 
                major_offset=major_offset
            )
    
    def parse(self, jianpu: List[Union[List, float, str]]) -> List[List[RelativeNote]]:
        """解析完整的简谱到相对音高"""
        
        parsed_jianpu = []
        current_major_offset = 0.0
        bar_count = 0
        
        logger.info(f"Starting to parse jianpu with {len(jianpu)} elements")
        
        for i, bar in enumerate(jianpu):
            # 处理调式偏移
            if isinstance(bar, (float, str)):
                try:
                    offset = float(bar)
                    if offset % 0.5 != 0:
                        raise ValueError(f"Invalid major offset: {offset}")
                    current_major_offset = offset
                    logger.info(f"Major offset changed to {current_major_offset}")
                    continue
                except ValueError as e:
                    logger.error(f"Invalid major offset at position {i}: {e}")
                    raise
            
            # 解析小节
            parsed_bar = []
            try:
                self.parse_recursively(
                    bar, 
                    parsed_bar, 
                    time_factor=2.0, 
                    major_offset=current_major_offset
                )
                
                # 扩展音域定义（如果需要）
                max_height = max((note.relative_height for note in parsed_bar 
                                if note.relative_height is not None), default=0)
                min_height = min((note.relative_height for note in parsed_bar 
                                if note.relative_height is not None), default=0)
                
                range_span = max_height - min_height
                if range_span > 0:
                    self.notation.extend_range(max_height)
                
                parsed_jianpu.append(parsed_bar)
                bar_count += 1
                logger.debug(f"Parsed bar {bar_count} with {len(parsed_bar)} notes")
                
            except Exception as e:
                logger.error(f"Error parsing bar {bar_count + 1}: {e}")
                raise
        
        logger.info(f"Successfully parsed {bar_count} bars to relative pitch system")
        return parsed_jianpu
    
    def get_range_info(self, parsed_jianpu: List[List[RelativeNote]]) -> dict:
        """获取解析结果的音域信息"""
        all_notes = []
        for bar in parsed_jianpu:
            all_notes.extend(bar)
        
        valid_heights = [note.relative_height for note in all_notes 
                        if note.relative_height is not None]
        
        if not valid_heights:
            return {"min": 0, "max": 0, "span": 0, "octaves": 0}
        
        min_height = min(valid_heights)
        max_height = max(valid_heights)
        span = max_height - min_height
        
        return {
            "min": min_height,
            "max": max_height, 
            "span": span,
            "octaves": span / 12.0,
            "note_count": len(valid_heights)
        }