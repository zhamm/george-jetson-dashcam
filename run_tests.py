#!/usr/bin/env python3
"""
Test runner for George Jetson Dashcam
Runs all unit and integration tests
"""
import sys
import os
import unittest
import argparse
from io import StringIO

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))


def run_tests(verbosity=2, pattern='test_*.py'):
    """
    Run all tests in the tests directory.
    
    Args:
        verbosity: Test output verbosity (0-2)
        pattern: Test file pattern to match
    
    Returns:
        TestResult object
    """
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), 'tests')
    suite = loader.discover(start_dir, pattern=pattern)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result


def run_specific_test(test_name, verbosity=2):
    """
    Run a specific test module or test case.
    
    Args:
        test_name: Name of test module (e.g., 'test_web_server')
        verbosity: Test output verbosity
    
    Returns:
        TestResult object
    """
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(f'tests.{test_name}')
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result


def print_coverage_summary(result):
    """Print test coverage summary."""
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}")
    
    print("=" * 70)


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description='Run George Jetson Dashcam tests')
    parser.add_argument(
        '-v', '--verbosity',
        type=int,
        choices=[0, 1, 2],
        default=2,
        help='Test output verbosity (0=quiet, 1=normal, 2=verbose)'
    )
    parser.add_argument(
        '-t', '--test',
        type=str,
        help='Run specific test module (e.g., test_web_server)'
    )
    parser.add_argument(
        '-p', '--pattern',
        type=str,
        default='test_*.py',
        help='Test file pattern to match'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available tests'
    )
    
    args = parser.parse_args()
    
    if args.list:
        # List all tests
        print("Available test modules:")
        test_dir = os.path.join(os.path.dirname(__file__), 'tests')
        for filename in sorted(os.listdir(test_dir)):
            if filename.startswith('test_') and filename.endswith('.py'):
                print(f"  - {filename[:-3]}")
        return 0
    
    print("=" * 70)
    print("GEORGE JETSON DASHCAM - TEST SUITE")
    print("=" * 70)
    print()
    
    # Run tests
    if args.test:
        print(f"Running specific test: {args.test}")
        print()
        result = run_specific_test(args.test, verbosity=args.verbosity)
    else:
        print(f"Running all tests (pattern: {args.pattern})")
        print()
        result = run_tests(verbosity=args.verbosity, pattern=args.pattern)
    
    # Print summary
    print_coverage_summary(result)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
