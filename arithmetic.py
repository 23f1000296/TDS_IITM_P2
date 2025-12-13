import re
from sympy import sympify

def solve_arithmetic(question: str):
    q = question.lower()

    # Direct expressions
    try:
        expr = re.findall(r"[0-9\+\-\*/\(\)\.]+", q)
        if expr:
            return float(sympify(expr[0]))
    except:
        pass

    nums = list(map(float, re.findall(r"\d+\.?\d*", q)))

    if "sum" in q or "total" in q:
        return sum(nums)

    if "difference" in q:
        return nums[0] - nums[1]

    if "product" in q or "multiply" in q:
        result = 1
        for n in nums:
            result *= n
        return result

    if "average" in q or "mean" in q:
        return sum(nums) / len(nums)

    if "percentage" in q:
        return (nums[0] / nums[1]) * 100

    return None
