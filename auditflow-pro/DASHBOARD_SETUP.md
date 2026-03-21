# AuditFlow-Pro Banking Dashboard - Setup Guide

## Quick Start

### 1. Install Dependencies

Navigate to the frontend directory and install the required packages:

```bash
cd auditflow-pro/frontend
npm install
```

This will install Recharts (v2.10.3) and all other dependencies needed for the dashboard.

### 2. Start the Development Server

```bash
npm run dev
```

The application will start on `http://localhost:5173` (or the next available port).

### 3. Access the Dashboard

1. Log in with your credentials
2. Navigate to the Dashboard page (default route after login)
3. Or click "Dashboard" in the sidebar navigation

## What's Included

### New Files Created

1. **`auditflow-pro/frontend/src/pages/Dashboard.tsx`**
   - Main dashboard component with all visualizations
   - 400+ lines of React/TypeScript code
   - Fully responsive design
   - Interactive charts and metrics

2. **`auditflow-pro/frontend/DASHBOARD_README.md`**
   - Comprehensive documentation
   - Feature descriptions
   - Technical stack details
   - Usage instructions

### Modified Files

1. **`auditflow-pro/frontend/package.json`**
   - Added `recharts: ^2.10.3` dependency

2. **`auditflow-pro/frontend/src/App.tsx`**
   - Updated import to use new Dashboard page component
   - Changed from `./components/dashboard/Dashboard` to `./pages/Dashboard`

## Dashboard Features

### Key Metrics
- 70k Active Accounts
- 152 Pending Loan Applications
- 80 Fraud Alerts

### Visualizations
- **AI-Powered Fraud Detection**: Line chart showing detected vs. predicted fraud
- **Core Banking Health**: Semi-circular gauge showing 93% health
- **Cash Flow Analytics**: Bar chart with inflow ($25.4M) and outflow ($18.2M)
- **Compliance Status Tracker**: Donut chart with AML, KYC, GDPR compliance
- **Reconciliation Accuracy Trend**: Area chart showing 83% accuracy
- **Quick Stats**: Transaction count, success rate, response time, failed transactions

### System Notifications
- High-risk transaction alerts
- Compliance check notifications
- System maintenance alerts
- Color-coded severity levels
- "Take Action" buttons for each alert

## Design Highlights

### Modern Banking Aesthetic
- Clean, professional card-based layout
- Blue, red, and gray color scheme
- Consistent spacing and typography
- Smooth animations and transitions

### Responsive Design
- Desktop: Multi-column layouts with full charts
- Tablet: 2-column grid layouts
- Mobile: Single-column stacked layout

### Interactive Elements
- Hover tooltips on all charts
- Interactive data points
- Smooth animations
- Color-coded severity indicators

## Technology Stack

- **React 18.3.1**: UI framework
- **TypeScript**: Type safety and better IDE support
- **Tailwind CSS**: Utility-first CSS framework
- **Recharts 2.10.3**: React charting library
- **Lucide React**: Icon library

## File Structure

```
auditflow-pro/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   └── Dashboard.tsx (NEW)
│   │   ├── App.tsx (MODIFIED)
│   │   └── ...
│   ├── package.json (MODIFIED)
│   ├── DASHBOARD_README.md (NEW)
│   └── ...
└── DASHBOARD_SETUP.md (NEW - this file)
```

## Troubleshooting

### Module Not Found Error
If you see "Cannot find module 'recharts'":
```bash
npm install recharts@^2.10.3
```

### Port Already in Use
If port 5173 is already in use, Vite will automatically use the next available port.

### TypeScript Errors
Ensure you're using TypeScript 5.9.3 or later:
```bash
npm install typescript@~5.9.3
```

## Next Steps

### To Customize the Dashboard

1. **Update Mock Data**: Edit the data objects at the top of `Dashboard.tsx`
2. **Change Colors**: Modify the color values in the COLORS array
3. **Add New Charts**: Use Recharts components to add additional visualizations
4. **Connect to API**: Replace mock data with real API calls

### To Integrate Real Data

1. Create API service methods in `src/services/api.ts`
2. Use React hooks (useState, useEffect) to fetch data
3. Replace mock data with API responses
4. Add loading and error states

### Example API Integration

```typescript
const [data, setData] = useState(null);
const [loading, setLoading] = useState(true);

useEffect(() => {
  const fetchData = async () => {
    try {
      const response = await fetch('/api/dashboard/metrics');
      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };
  
  fetchData();
}, []);
```

## Performance Tips

1. **Lazy Load Charts**: Use React.lazy() for chart components
2. **Memoize Components**: Use React.memo() to prevent unnecessary re-renders
3. **Optimize Data**: Limit chart data points to 12-24 for better performance
4. **Use Virtual Scrolling**: For long notification lists

## Browser Compatibility

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Support

For issues or questions:
1. Check the DASHBOARD_README.md for detailed documentation
2. Review the component code in `src/pages/Dashboard.tsx`
3. Check browser console for error messages
4. Verify all dependencies are installed with `npm list`

## Production Deployment

Before deploying to production:

1. Build the application:
   ```bash
   npm run build
   ```

2. Test the build locally:
   ```bash
   npm run preview
   ```

3. Verify all charts render correctly
4. Test responsive design on various devices
5. Check performance with browser DevTools

## License

This dashboard is part of the AuditFlow-Pro application and follows the same license terms.
