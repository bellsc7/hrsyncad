# Fix for Missing FTP Sync Icon

## Issue Identified
The FTP sync icon in the dashboard is not displaying because the icon class `bi-file-earrow-arrow-down` doesn't exist in Bootstrap Icons version 1.10.0.

## Root Cause
The correct icon class should be `bi-file-earmark-arrow-down` (with "earmark" instead of "earrow").

## Files to Modify
1. `app/templates/dashboard.html` - Line 51
2. `app/templates/dashboard copy.html` - Line 51

## Changes Required
Replace:
```html
<i class="bi bi-file-earrow-arrow-down display-4 text-success"></i>
```

With:
```html
<i class="bi bi-file-earmark-arrow-down display-4 text-success"></i>
```

## Alternative Icon Options
If the above fix doesn't work, consider these alternative icons for FTP sync:
- `bi-file-arrow-down`
- `bi-download`
- `bi-cloud-download`
- `bi-server` (for FTP server)

## Testing Steps
1. Apply the fix to both HTML files
2. Load the dashboard in a browser
3. Verify the FTP sync icon is now visible
4. Check that the icon styling (size and color) is consistent with other icons