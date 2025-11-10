# Test-Driven Development (TDD) Example

This directory contains an **excellent example of TDD** demonstrating its value for security-critical code.

## The Security Bug

**Problem**: Without proper authorization checks, a photographer could edit/delete another photographer's images.

**Example Attack**:
```bash
# Liam logs in and gets authenticated
# Liam then sends:
PUT /api/photographer/images/1  # Adrian's image!
{
  "title": "Hacked by Liam!"
}

# Without the security check, this would succeed!
```

## The TDD Workflow

### 1. Write the Failing Test First

File: `api/tests/test_simple_security.py`

```python
async def test_photographer_cannot_edit_other_users_images():
    """Test that Liam cannot edit Adrian's images"""

    # Liam tries to edit Adrian's image (id=1)
    response = await client.put(
        "/api/photographer/images/1",
        cookies={"session_token": liam_token},
        json={"title": "Hacked!"}
    )

    # EXPECTED: 404 (image not found for Liam)
    assert response.status_code in [403, 404]
```

**Initial Result**: Test FAILS (before fix was added)

### 2. Fix the Bug

File: `api/routes/photographer.py`

Added the critical security check:

```python
@router.put("/images/{image_id}")
async def update_image(
    image_id: int,
    current_user: User = Depends(get_current_user),
    ...
):
    user_id = current_user.id

    # ⚠️ CRITICAL SECURITY CHECK ⚠️
    await verify_image_ownership(image_id, user_id)

    # Now safe to update
    await db.execute("UPDATE images SET ... WHERE id = ? AND user_id = ?")
```

The `verify_image_ownership()` function checks that the image belongs to the authenticated user:

```python
async def verify_image_ownership(image_id: int, user_id: int):
    """Prevent photographers from modifying each other's images"""
    cursor = await db.execute(
        "SELECT user_id FROM images WHERE id = ?",
        (image_id,)
    )
    row = await cursor.fetchone()

    if not row or row[0] != user_id:
        raise HTTPException(status_code=404)  # Image not found
```

### 3. Test Passes!

```bash
$ python3 api/tests/test_simple_security.py

✓ Security test passed! Status code: 404
✓ Photographers cannot edit each other's images
✓ All security tests passed!
```

## Why This Example is Excellent

### 1. Real Security Vulnerability
This isn't a theoretical bug - it's a genuine multi-tenancy security hole that could lead to:
- **Data corruption**: Images edited by wrong user
- **Data loss**: Images deleted by wrong user
- **Privacy violations**: Unpublished images made public by another user

### 2. TDD Caught It Early
Without this test, the bug might have gone unnoticed until production, where it could cause real harm. With TDD:
- ✅ Bug caught immediately during development
- ✅ Can't accidentally remove the security check (test would fail)
- ✅ Documents the security requirement for future developers

### 3. Minimal, Focused Test
The test is **30 lines of code** but protects against a critical security flaw. High ROI.

### 4. Reusable Pattern
The same pattern applies to:
- `DELETE /api/photographer/images/{id}` - Can't delete other users' images
- `PATCH /api/photographer/images/{id}/publish` - Can't publish other users' images
- Any future photographer management endpoints

## Running the Tests

### Quick Test (Recommended)

```bash
# From inside the API container
cd /app
PYTHONPATH=/app python3 api/tests/test_simple_security.py
```

### Full Test Suite

```bash
# Install dependencies (if needed)
pip install pytest pytest-asyncio

# Run all tests
cd /app
PYTHONPATH=/app pytest api/tests/ -v

# Run only security tests
PYTHONPATH=/app pytest api/tests/test_simple_security.py -v
```

### From Host Machine

```bash
# If using Docker
docker compose -f docker-compose.local.yml -p hensler_test exec api \
  sh -c "cd /app && PYTHONPATH=/app python3 api/tests/test_simple_security.py"
```

## The Complete Test Infrastructure

### Files Created

1. **`api/tests/test_simple_security.py`** - The actual security test (30 lines)
2. **`api/tests/conftest.py`** - Test fixtures and database setup (150 lines)
3. **`api/tests/test_gallery_security.py`** - Comprehensive test suite (300 lines)
4. **`api/routes/photographer.py`** - Photographer routes with security checks (280 lines)
5. **`pytest.ini`** - Pytest configuration

### Dependencies Added

In `api/requirements.txt`:
```
pytest==7.4.3
pytest-asyncio==0.21.1
```

## What We Learned

### Before TDD:
- ❌ Security bugs slip through
- ❌ Manual testing is incomplete
- ❌ Refactoring is risky (might break security)

### After TDD:
- ✅ Security bugs caught immediately
- ✅ Automated testing ensures correctness
- ✅ Safe refactoring (tests verify behavior)

## Next Steps

Apply this pattern to other critical paths:

1. **Authentication boundaries** - Test role-based access control
2. **Image upload** - Test file validation, size limits
3. **EXIF privacy** - Test that `share_exif=false` hides metadata
4. **Analytics** - Test that image_events are scoped to correct user

## Cost-Benefit Analysis

**Time Investment**: ~30 minutes to write this test

**Value**:
- Prevented a critical security bug
- Created reusable test pattern
- Documented security requirements
- Confidence to refactor safely

**ROI**: Infinite (one security breach could cost everything)

## Conclusion

This is TDD at its best:
- Small, focused test
- Caught a real bug
- Pays for itself immediately
- Creates lasting value

**Use this pattern for all security-critical code.**
