def calculate_provided_data():
    """
    Calculate the sum of the provided Perdida al tipo de cambio Monitor column data
    """
    
    # The data provided by the user
    perdida_values = [
        -168, -335, -29, -14, -7, -8, -29, -6847, -85, -88, -492, -36, -64, -7, -112, -16, 0, -920, -293, -143, -304, -2246, -240, -229, -1552, -171, -60, -423, -153, -694, -694, -50, -40, -40, -40, -50, -554, -308, -731, -1315, -114, -4926, -46, -1550, -82, -33, -890, -479, -208, -42, -38, -81, -116, -20074, -779, -948, -238, -151, -209, -267, -448, -389, -446, -298, -314, -679, -941, -638, -486, -171, -2078, 332, -732, -3656, -1108, -823, -559, -164, -1389, -427, 34, -881, -911, -1320, -665, -428, -881, -463, -319, -257, -1404, -3967, -221, -177, -211, -224, -281, -2057, -163, -171, -1959, -240, -224, -1376, -345, 573, 409, 409, -367, -172, -599, -386, -573, -638, -3202, -1572, 916, -165, -573, 6367, -2809, -597, -628, -4924, -218, -82, -1953, -9, -9, -1049, -4456, -1298, -603, -613, -178, -1459, -67, -3, -3, -3, -4364, -2216, -784, -138, -823, -716, -6341, -1972, -431, -409, -65, -26, -2216, -2216, -129, 0, -1, -2, -2, -1, -5, -6, -1538, -218, -400, -3399, -431, -300, -106, -19, -634, -284, -383, -3814, -286, -3699, -1075, -117, 104, -4429, -416, -2524, 457, -4828, -4612, -601, -406, -1519, -43, -68, -1232, -366, -152, -8203, -1167, -812, -7469, -812, 25, -993, -2131, -244, -836, -904, -6, -2251, -2885, -109, -2107, -76, -875, -35, -3062, -123, -459, -16, -3878
    ]
    
    print("=== ANALYZING PROVIDED PERDIDA DATA ===\n")
    
    # Calculate basic statistics
    total_count = len(perdida_values)
    total_sum = sum(perdida_values)
    absolute_sum = abs(total_sum)
    
    print(f"1. Basic Statistics:")
    print(f"   Total values: {total_count}")
    print(f"   Sum (with sign): ${total_sum:,.2f}")
    print(f"   Absolute sum: ${absolute_sum:,.2f}")
    print(f"   Average: ${total_sum/total_count:,.2f}")
    print(f"   Min value: ${min(perdida_values):,.2f}")
    print(f"   Max value: ${max(perdida_values):,.2f}")
    
    # Count positive vs negative
    positive_values = [v for v in perdida_values if v > 0]
    negative_values = [v for v in perdida_values if v < 0]
    zero_values = [v for v in perdida_values if v == 0]
    
    print(f"\n2. Value Distribution:")
    print(f"   Positive values: {len(positive_values)} (sum: ${sum(positive_values):,.2f})")
    print(f"   Negative values: {len(negative_values)} (sum: ${sum(negative_values):,.2f})")
    print(f"   Zero values: {len(zero_values)}")
    
    # Compare with expected values
    expected_205550 = 205550
    expected_202414 = 202414
    
    print(f"\n3. Comparison with Expected Values:")
    print(f"   Your expected value: ${expected_205550:,.2f}")
    print(f"   Current dashboard: ${expected_202414:,.2f}")
    print(f"   Provided data absolute: ${absolute_sum:,.2f}")
    
    diff_from_expected = absolute_sum - expected_205550
    diff_from_dashboard = absolute_sum - expected_202414
    
    print(f"\n   Differences:")
    print(f"   From expected $205,550: ${diff_from_expected:,.2f}")
    print(f"   From dashboard $202,414: ${diff_from_dashboard:,.2f}")
    
    # Check if this matches any of our previous calculations
    print(f"\n4. Analysis:")
    if abs(diff_from_expected) < 1000:
        print(f"   ✓ Very close to your expected $205,550!")
    elif abs(diff_from_dashboard) < 1000:
        print(f"   ✓ Very close to current dashboard value!")
    elif abs(diff_from_expected) < 5000:
        print(f"   ≈ Reasonably close to expected value (within $5k)")
    else:
        print(f"   ⚠ Significant difference from both expected values")
    
    # Show top 10 largest absolute values
    print(f"\n5. Top 10 Largest Absolute Values:")
    abs_values = [(abs(v), v) for v in perdida_values]
    abs_values.sort(reverse=True)
    
    for i, (abs_val, orig_val) in enumerate(abs_values[:10]):
        print(f"   {i+1}. ${orig_val:,.2f} (absolute: ${abs_val:,.2f})")
    
    return absolute_sum

if __name__ == "__main__":
    result = calculate_provided_data()
