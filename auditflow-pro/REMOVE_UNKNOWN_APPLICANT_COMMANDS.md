# Remove "Unknown Applicant" from Frontend - Commands

**Goal:** Remove or replace "Unknown Applicant" fallback text in the frontend

**Files to Update:** 4 files

---

## Files with "Unknown Applicant" Display

### 1. Dashboard.tsx
**File:** `frontend/src/components/dashboard/Dashboard.tsx`
**Line:** 112

**Current:**
```tsx
{audit.applicant_name || 'Unknown'}
```

**Change to:**
```tsx
{audit.applicant_name || '-'}
```

Or remove the fallback entirely:
```tsx
{audit.applicant_name}
```

---

### 2. AuditDetailView.tsx
**File:** `frontend/src/components/audit/AuditDetailView.tsx`
**Line:** 205

**Current:**
```tsx
{audit.applicant_name || (audit.golden_record?.name?.value) || (audit.golden_record?.first_name?.value && audit.golden_record?.last_name?.value ? `${audit.golden_record.first_name.value} ${audit.golden_record.last_name.value}` : 'N/A')}
```

**Change to:**
```tsx
{audit.applicant_name || audit.golden_record?.name?.value || (audit.golden_record?.first_name?.value && audit.golden_record?.last_name?.value ? `${audit.golden_record.first_name.value} ${audit.golden_record.last_name.value}` : '-')}
```

---

### 3. AuditQueue.tsx
**File:** `frontend/src/components/dashboard/AuditQueue.tsx`
**Line:** 221

**Current:**
```tsx
<div className="text-sm text-gray-500">{audit.applicant_name || 'Processing...'}</div>
```

**Change to:**
```tsx
<div className="text-sm text-gray-500">{audit.applicant_name || 'Processing...'}</div>
```

(This one already shows "Processing..." which is better)

---

### 4. AuditRecords.tsx
**File:** `frontend/src/pages/AuditRecords.tsx`
**Line:** 143

**Current:**
```tsx
{audit.applicant_name || 'Unknown'}
```

**Change to:**
```tsx
{audit.applicant_name || '-'}
```

Or remove the fallback:
```tsx
{audit.applicant_name}
```

---

## Quick Fix Commands

### Option 1: Replace "Unknown" with "-" (Recommended)

```bash
# Dashboard.tsx
sed -i "s/{audit.applicant_name || 'Unknown'}/{audit.applicant_name || '-'}/g" auditflow-pro/frontend/src/components/dashboard/Dashboard.tsx

# AuditRecords.tsx
sed -i "s/{audit.applicant_name || 'Unknown'}/{audit.applicant_name || '-'}/g" auditflow-pro/frontend/src/pages/AuditRecords.tsx
```

### Option 2: Remove Fallback Entirely

```bash
# Dashboard.tsx
sed -i "s/{audit.applicant_name || 'Unknown'}/{audit.applicant_name}/g" auditflow-pro/frontend/src/components/dashboard/Dashboard.tsx

# AuditRecords.tsx
sed -i "s/{audit.applicant_name || 'Unknown'}/{audit.applicant_name}/g" auditflow-pro/frontend/src/pages/AuditRecords.tsx
```

### Option 3: Replace with "N/A"

```bash
# Dashboard.tsx
sed -i "s/{audit.applicant_name || 'Unknown'}/{audit.applicant_name || 'N\/A'}/g" auditflow-pro/frontend/src/components/dashboard/Dashboard.tsx

# AuditRecords.tsx
sed -i "s/{audit.applicant_name || 'Unknown'}/{audit.applicant_name || 'N\/A'}/g" auditflow-pro/frontend/src/pages/AuditRecords.tsx
```

---

## Manual Fix (Using Editor)

### File 1: Dashboard.tsx

1. Open `auditflow-pro/frontend/src/components/dashboard/Dashboard.tsx`
2. Find line 112: `{audit.applicant_name || 'Unknown'}`
3. Replace with: `{audit.applicant_name || '-'}`
4. Save

### File 2: AuditDetailView.tsx

1. Open `auditflow-pro/frontend/src/components/audit/AuditDetailView.tsx`
2. Find line 205: `{audit.applicant_name || (audit.golden_record?.name?.value) || ... 'N/A'}`
3. Replace `'N/A'` at the end with `'-'`
4. Save

### File 3: AuditQueue.tsx

1. Open `auditflow-pro/frontend/src/components/dashboard/AuditQueue.tsx`
2. Line 221 already shows `'Processing...'` which is good
3. No change needed (or change to `'-'` if you prefer)

### File 4: AuditRecords.tsx

1. Open `auditflow-pro/frontend/src/pages/AuditRecords.tsx`
2. Find line 143: `{audit.applicant_name || 'Unknown'}`
3. Replace with: `{audit.applicant_name || '-'}`
4. Save

---

## Verify Changes

After making changes, verify the files:

```bash
# Check Dashboard.tsx
grep -n "applicant_name" auditflow-pro/frontend/src/components/dashboard/Dashboard.tsx | grep -v "test"

# Check AuditRecords.tsx
grep -n "applicant_name" auditflow-pro/frontend/src/pages/AuditRecords.tsx

# Check AuditDetailView.tsx
grep -n "applicant_name" auditflow-pro/frontend/src/components/audit/AuditDetailView.tsx

# Check AuditQueue.tsx
grep -n "applicant_name" auditflow-pro/frontend/src/components/dashboard/AuditQueue.tsx
```

---

## Recommended Approach

**Replace "Unknown" with "-"** (Option 1)

This is the best approach because:
- ✓ Shows clearly that data is missing
- ✓ Doesn't confuse users with "Unknown"
- ✓ Consistent with data tables
- ✓ Professional appearance

---

## After Making Changes

1. **Rebuild frontend:**
   ```bash
   cd auditflow-pro/frontend
   npm run build
   ```

2. **Test locally:**
   ```bash
   npm run dev
   ```

3. **Verify in browser:**
   - Check audit queue
   - Check audit detail view
   - Verify applicant names display correctly

---

## Summary

**Files to update:** 4
- Dashboard.tsx (line 112)
- AuditRecords.tsx (line 143)
- AuditDetailView.tsx (line 205)
- AuditQueue.tsx (line 221) - optional

**Recommended change:** Replace `'Unknown'` with `'-'`

**Quick command:**
```bash
sed -i "s/{audit.applicant_name || 'Unknown'}/{audit.applicant_name || '-'}/g" auditflow-pro/frontend/src/components/dashboard/Dashboard.tsx && \
sed -i "s/{audit.applicant_name || 'Unknown'}/{audit.applicant_name || '-'}/g" auditflow-pro/frontend/src/pages/AuditRecords.tsx
```

