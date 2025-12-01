# Features Checklist

- [x] **Consolidate Application Backends**: Restrict "Application Backend" to a single layer in the main list, with multiple backends defined as `nodes` within it. Update UI to reflect this.
- [x] **Strict Layer Architecture**: Enforce fixed 4-layer slots (CDN, LB, Proxy, Backend) in the UI, preventing arbitrary layer addition/ordering.
- [ ] **Visual Routing Logic**: Add visual indicators in the UI to show routing rules connecting layers to specific nodes.
