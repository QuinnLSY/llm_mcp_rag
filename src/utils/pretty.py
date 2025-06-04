from dataclasses import dataclass
import rich
from rich.console import Console
from rich.rule import Rule
from rich.text import Text
from rich import print as rprint

RICH_CONSOLE = Console()

@dataclass
class ALogger:
    """日志装饰器类，用于输出带样式的标题"""
    
    prefix:  str = ""  # 前缀文本
    
    def title(self, text: str | Text, rule_style="blink bright_green"):
        """输出带前缀的装饰性标题
        
        Args:
            text (str | Text): 标题文本，可以是字符串或富文本对象
            rule_style (str, optional): 标题装饰线的样式
        """
        lists = []
        if self.prefix:
            lists.append(rich.markup.escape(self.prefix))  # 添加转义后的前缀
        if text:
            lists.append(text)  # 添加标题文本
        rprint(Rule(title=" ".join(lists), style=rule_style))  # 打印带标题的装饰线

def log_title(text: str | Text, rule_style="bright_green"):
    """快速打印装饰性标题（不带前缀）
    
    Args:
        text (str | Text): 标题文本
        rule_style (str, optional): 装饰线样式
    """
    objs = []
    if text:
        objs.append(Rule(title=text, style=rule_style))  # 创建装饰线对象
    rprint(*objs)  # 打印装饰线

if __name__ == "__main__":
    # log_title("hello world")  # 示例用法
    ALogger("[utils]").title("hello world")