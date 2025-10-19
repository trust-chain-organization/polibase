# ⚠️ DEPRECATED: Legacy Streamlit Interface

**This directory is deprecated and will be removed in a future version.**

## Migration Notice

This legacy Streamlit interface has been superseded by the new Clean Architecture implementation.

### New Location

```
src/interfaces/web/streamlit/
```

### How to Use the New Interface

**Via CLI Command (Recommended):**
```bash
uv run polibase streamlit
```

**Direct Execution:**
```bash
streamlit run src/interfaces/web/streamlit/app.py
```

### Architecture Changes

The new implementation follows Clean Architecture principles:

```
src/interfaces/web/streamlit/
├── app.py                 # Main Streamlit application entry point
├── views/                 # UI views for each entity
│   ├── meetings_view.py
│   ├── politicians_view.py
│   ├── conferences_view.py
│   └── ...
├── presenters/            # Business logic presentation layer
│   ├── meeting_presenter.py
│   ├── politician_presenter.py
│   └── ...
├── components/            # Reusable UI components
│   ├── forms/
│   ├── tables/
│   └── charts/
├── dto/                   # Data Transfer Objects
│   ├── request/
│   └── response/
└── utils/                 # UI utilities
    ├── session_manager.py
    └── error_handler.py
```

### Benefits of the New Structure

1. **Separation of Concerns**: Business logic separated from UI
2. **Testability**: Presenters can be unit tested independently
3. **Reusability**: Components can be shared across views
4. **Type Safety**: DTOs provide clear data contracts
5. **Maintainability**: Clear structure makes code easier to understand

### Migration Path

If you have custom code in this directory:

1. Move view logic to `src/interfaces/web/streamlit/views/`
2. Extract business logic to presenters in `src/interfaces/web/streamlit/presenters/`
3. Create DTOs for data transfer in `src/interfaces/web/streamlit/dto/`
4. Move reusable components to `src/interfaces/web/streamlit/components/`

### Timeline

- **Current**: Legacy interface still functional with deprecation notice
- **v1.x**: Deprecation warnings added
- **v2.0**: Legacy interface will be removed

### Support

For questions or migration assistance, please:
- Check the documentation: `docs/CLEAN_ARCHITECTURE_MIGRATION.md`
- Review the analysis: `tmp/clean_architecture_analysis_2025.md`
- Open an issue: https://github.com/trust-chain-organization/polibase/issues

---

**Last Updated**: 2025-10-19
**Status**: Deprecated
**Removal Target**: v2.0
