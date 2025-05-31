# Deployment Checklist for TubeScribe

## Pre-deployment

- [ ] Test the application locally using `python dev_server.py`
- [ ] Verify all API endpoints work with sample YouTube URLs
- [ ] Check responsive design on different screen sizes
- [ ] Ensure error handling works properly
- [ ] Test clipboard functionality
- [ ] Test file download functionality

## Vercel Configuration

- [ ] `vercel.json` is properly configured
- [ ] `requirements.txt` contains all Python dependencies
- [ ] API functions are in the `/api` directory
- [ ] Each API function has proper CORS headers

## Testing After Deployment

- [ ] Test with various YouTube video URLs
- [ ] Test subtitle tracks in different languages
- [ ] Test auto-generated vs manual subtitles
- [ ] Verify metadata inclusion/exclusion works
- [ ] Test error scenarios (invalid URLs, videos without subtitles)
- [ ] Check mobile responsiveness
- [ ] Verify performance (should load quickly)

## Post-deployment

- [ ] Update repository README with live demo URL
- [ ] Add monitoring/analytics if needed
- [ ] Document any known limitations
- [ ] Set up error reporting if desired

## Common Issues

### API Functions Not Working
- Check that Python runtime is set to 3.9 in vercel.json
- Verify CORS headers are properly set
- Ensure all imports are available in the serverless environment

### YouTube Access Issues
- YouTube may block requests from certain IPs
- Consider adding retry logic for temporary failures
- Monitor for changes in YouTube's page structure

### Performance Issues
- Large subtitle files may take time to process
- Consider adding progress indicators for long operations
- Optimize parsing logic if needed
