# Bugfix Requirements Document

## Introduction

When users log in with a temporary password that requires a password change, AWS Cognito returns a NEW_PASSWORD_REQUIRED challenge. The application should display a new password form to allow users to set their permanent password. However, the new password form does not appear, leaving users unable to complete the login process.

This bug affects users logging in for the first time or when an administrator has forced a password reset. The issue stems from a mismatch between the challenge name value returned by AWS Amplify v6 (`CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED`) and the value the Login component checks for (`NEW_PASSWORD_REQUIRED`).

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user logs in with credentials that trigger a NEW_PASSWORD_REQUIRED challenge from Cognito THEN the system returns `challengeName: "CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED"` from the login function

1.2 WHEN the Login component receives `challengeName: "CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED"` THEN the system fails to match it against the hardcoded string `'NEW_PASSWORD_REQUIRED'` and does not display the new password form

1.3 WHEN the new password form does not appear THEN the user remains on the login screen without any indication of what to do next

### Expected Behavior (Correct)

2.1 WHEN a user logs in with credentials that trigger a NEW_PASSWORD_REQUIRED challenge from Cognito THEN the system SHALL correctly identify the challenge using the Amplify v6 value `"CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED"`

2.2 WHEN the Login component receives the NEW_PASSWORD_REQUIRED challenge (in any valid format) THEN the system SHALL display the new password form with password requirements

2.3 WHEN the new password form is displayed THEN the user SHALL be able to enter and submit a new password that meets Cognito's password policy requirements

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user logs in with valid permanent credentials (no challenge required) THEN the system SHALL CONTINUE TO redirect to the dashboard successfully

3.2 WHEN a user enters incorrect credentials THEN the system SHALL CONTINUE TO display appropriate error messages without showing the new password form

3.3 WHEN a user completes the new password challenge successfully THEN the system SHALL CONTINUE TO redirect to the dashboard and establish an authenticated session

3.4 WHEN a user submits a new password that doesn't meet requirements THEN the system SHALL CONTINUE TO display validation errors without attempting to submit to Cognito
