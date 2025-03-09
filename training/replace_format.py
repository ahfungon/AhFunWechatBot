import re
import json
import os
import sys
from decimal import Decimal, getcontext

# 设置小数精度
getcontext().prec = 28

def process_file(file_path):
    """处理文件，替换所有x±3%格式为x*0.97-x*1.03格式"""
    print(f"处理文件: {file_path}")
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 定义替换函数
    def replace_format(match):
        # 提取数字部分
        number = Decimal(match.group(1))
        # 计算下限和上限
        lower = round(number * Decimal('0.97'), 2)
        upper = round(number * Decimal('1.03'), 2)
        # 返回替换后的格式
        return f"{lower}-{upper}"
    
    # 使用正则表达式查找并替换
    pattern = r'(\d+\.\d+)±3%'
    new_content = re.sub(pattern, replace_format, content)
    
    # 写入替换后的内容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    # 统计替换次数
    original_matches = re.findall(pattern, content)
    replacement_count = len(original_matches)
    print(f"替换了 {replacement_count} 处 'x±3%' 格式")
    
    # 打印一些替换示例
    if replacement_count > 0:
        print("\n替换示例:")
        for i, num in enumerate(original_matches[:5]):  # 最多显示5个示例
            lower = round(Decimal(num) * Decimal('0.97'), 2)
            upper = round(Decimal(num) * Decimal('1.03'), 2)
            print(f"  {num}±3% → {lower}-{upper}")
        
        if replacement_count > 5:
            print(f"  ... 以及其他 {replacement_count - 5} 处替换")
    
    return replacement_count

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python replace_format.py <文件路径1> [文件路径2 ...]")
        print("示例: python replace_format.py training/stock_training_data_01.jsonl")
        return
    
    total_replacements = 0
    for file_path in sys.argv[1:]:
        if os.path.isfile(file_path):
            replacements = process_file(file_path)
            total_replacements += replacements
        else:
            print(f"错误: 文件 '{file_path}' 不存在")
    
    print(f"\n总共替换了 {total_replacements} 处 'x±3%' 格式")

if __name__ == "__main__":
    main() 