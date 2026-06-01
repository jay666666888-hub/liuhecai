#!/usr/bin/env python3
"""
测试号码选择验证器
"""
import pytest
import sys
sys.path.insert(0, '/mnt/c/Users/Admin/liuhecai')

from predictor.validators import NumberSelectionValidator


def test_number_selection_evaluate_hit():
    """特码在预测列表中 = 命中"""
    validator = NumberSelectionValidator()
    prediction = ["01", "05", "12", "23", "34", "45"]
    actual = "45"
    actual_list = ["雞", "猴", "兔", "羊", "豬", "馬", "狗"]

    result = validator.evaluate(prediction, actual_list, actual)
    assert result == True


def test_number_selection_evaluate_miss():
    """特码不在预测列表中 = 未中"""
    validator = NumberSelectionValidator()
    prediction = ["01", "05", "12", "23", "34", "45"]
    actual = "47"  # 不在列表中
    actual_list = ["龍", "龍", "虎", "牛", "豬", "虎", "鼠"]

    result = validator.evaluate(prediction, actual_list, actual)
    assert result == False


def test_number_selection_evaluate_empty():
    """空预测列表 = 未中"""
    validator = NumberSelectionValidator()
    prediction = []
    actual = "45"

    result = validator.evaluate(prediction, [], actual)
    assert result == False


def test_number_selection_evaluate_no_actual():
    """无特码 = 未中"""
    validator = NumberSelectionValidator()
    prediction = ["01", "05", "12", "23", "34", "45"]
    actual = None

    result = validator.evaluate(prediction, [], actual)
    assert result == False