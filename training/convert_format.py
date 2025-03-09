#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os

def convert_file_format(input_file, output_file=None):
    """
    将包含在数组中的jsonl数据转换为标准的jsonl格式
    每行一个独立的JSON对象，不包含外层数组
    """
    if output_file is None:
        # 如果没有指定输出文件，则在原文件名基础上添加_converted后缀
        base_name, ext = os.path.splitext(input_file)
        output_file = f"{base_name}_converted{ext}"
    
    try:
        # 读取输入文件
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析JSON数据
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            print(f"错误：{input_file} 不是有效的JSON格式")
            return False
        
        # 检查是否为数组格式
        if not isinstance(data, list):
            print(f"错误：{input_file} 不是数组格式，无需转换")
            return False
        
        # 打开输出文件
        with open(output_file, 'w', encoding='utf-8') as f:
            # 遍历数组中的每个对象，将其转换为标准jsonl格式
            for item in data:
                # 将每个对象转换为JSON字符串并写入文件
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print(f"转换成功！输出文件：{output_file}")
        return True
    
    except Exception as e:
        print(f"转换过程中发生错误：{str(e)}")
        return False

def main():
    # 设置输入文件路径
    input_file = "stock_training_data_01.json"
    
    # 设置输出文件路径
    output_file = "stock_training_data_01_standard.jsonl"
    
    # 执行转换
    success = convert_file_format(input_file, output_file)
    
    if success:
        print("文件格式转换完成！")
    else:
        print("文件格式转换失败！")

if __name__ == "__main__":
    main() 