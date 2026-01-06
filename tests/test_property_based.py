"""属性测试示例。

演示如何使用Hypothesis进行属性测试。
"""
import pytest
from hypothesis import given, strategies as st

def test_string_length_property():
    """测试字符串长度属性。"""
    @given(st.text())
    def property_test(s):
        # 属性：字符串长度总是非负的
        assert len(s) >= 0
        # 属性：空字符串长度为0
        if s == "":
            assert len(s) == 0

    property_test()

def test_list_append_property():
    """测试列表追加属性。"""
    @given(st.lists(st.integers()), st.integers())
    def property_test(lst, item):
        original_length = len(lst)
        lst.append(item)
        # 属性：追加元素后列表长度增加1
        assert len(lst) == original_length + 1
        # 属性：最后一个元素是追加的元素
        assert lst[-1] == item

    property_test()

def test_tag_name_validation_property():
    """测试标签名称验证属性。"""
    @given(st.text(min_size=1, max_size=100))
    def property_test(tag_name):
        # 属性：有效的标签名称应该通过基本验证
        # 这里只是示例，实际实现会在后续任务中完成
        assert isinstance(tag_name, str)
        assert len(tag_name) > 0
        assert len(tag_name) <= 100

    property_test()
