# PR #192 CI Failures Analysis

**Date**: 2025-01-23  
**PR**: #192 - Fix PDF URL verification in quality command  
**Status**: 🔴 Failed checks

## Failed Checks Summary

### 1. PR Checks - Check PR Title (❌ FAILED)
**Error**: No release type found in pull request title
- PR title: "Fix PDF URL verification in quality command"
- Required: Conventional commit format with prefix
- Available types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert

### 2. Pre-commit (❌ FAILED)
**Status**: Failed with exit code 1
- Details not fully visible in logs
- Need to run pre-commit locally to identify specific issues

### 3. Test (⏳ PENDING)
- Tests haven't run yet due to pre-commit failure

## Action Items

1. **Fix PR title** to use conventional commit format
2. **Run pre-commit locally** to identify and fix issues
3. **Ensure all tests pass** after pre-commit fixes

## Progress Tracking

### PR Title Fix
- [ ] Change title to: "fix: improve PDF URL verification in quality command"

### Pre-commit Issues
- [ ] Run pre-commit locally
- [ ] Fix any formatting issues
- [ ] Fix any linting issues
- [ ] Verify all hooks pass

### Testing
- [ ] Run unit tests locally
- [ ] Ensure no regressions

## Investigation Log

### 2025-01-23 - Initial Analysis
- Identified PR title needs conventional commit format
- Pre-commit failed but need to run locally for details
- Tests pending due to pre-commit failure