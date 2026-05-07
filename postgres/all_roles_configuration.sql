-- ============================================================================
-- Superset Complete Role Configuration Script (Fixed)
-- Defines all roles with granular permissions for public weather ETL pipeline
-- ============================================================================

-- Get all existing roles first
SELECT 'Checking existing roles:' as info;
SELECT id, name FROM ab_role ORDER BY name;

-- Create or get Public role
INSERT INTO ab_role (name) VALUES ('Public') 
ON CONFLICT DO NOTHING;

-- Configure roles
DO $$ 
DECLARE 
    admin_role_id INT;
    alpha_role_id INT;
    gamma_role_id INT;
    sql_lab_role_id INT;
    public_role_id INT;
BEGIN
    -- Get role IDs
    SELECT id INTO admin_role_id FROM ab_role WHERE name = 'Admin';
    SELECT id INTO alpha_role_id FROM ab_role WHERE name = 'Alpha';
    SELECT id INTO gamma_role_id FROM ab_role WHERE name = 'Gamma';
    SELECT id INTO sql_lab_role_id FROM ab_role WHERE name = 'sql_lab';
    SELECT id INTO public_role_id FROM ab_role WHERE name = 'Public';
    
    -- ========================================================================
    -- ALPHA ROLE - Full data access: create/edit datasets, dashboards, charts
    -- ========================================================================
    DELETE FROM ab_permission_view_role WHERE role_id = alpha_role_id;
    
    INSERT INTO ab_permission_view_role (permission_view_id, role_id)
    SELECT DISTINCT pv.id, alpha_role_id
    FROM ab_permission_view pv
    INNER JOIN ab_permission p ON pv.permission_id = p.id
    INNER JOIN ab_view_menu vm ON pv.view_menu_id = vm.id
    WHERE vm.name NOT IN ('SecurityRestApi', 'RoleRestApi', 'UserDBModelView', 'UserInfoRestApi')
    AND p.name NOT IN ('all_database_access', 'all_datasource_access', 'all_query_access')
    ON CONFLICT (permission_view_id, role_id) DO NOTHING;
    
    -- ========================================================================
    -- GAMMA ROLE - Public users: explore + create charts (read-only on data)
    -- ========================================================================
    DELETE FROM ab_permission_view_role WHERE role_id = gamma_role_id;
    
    INSERT INTO ab_permission_view_role (permission_view_id, role_id)
    SELECT DISTINCT pv.id, gamma_role_id
    FROM ab_permission_view pv
    INNER JOIN ab_permission p ON pv.permission_id = p.id
    INNER JOIN ab_view_menu vm ON pv.view_menu_id = vm.id
    WHERE (vm.name IN ('Chart', 'Dashboard', 'Explore', 'Api', 'SQLLab', 'Superset', 'MenuApi', 
                       'DynamicPlugin', 'AvailableDomains', 'Tag', 'Datasets', 'Databases', 
                       'Dashboards', 'Charts', 'Data', 'ExploreFormDataRestApi', 'ExplorePermalinkRestApi'))
    AND (p.name IN ('can_read', 'can_write', 'can_query', 'can_query_form_data', 'can_estimate_query_cost',
                    'menu_access', 'can_show', 'can_get', 'can_run_async_queries', 'can_execute_sql_query',
                    'can_access'))
    ON CONFLICT (permission_view_id, role_id) DO NOTHING;
    
    -- ========================================================================
    -- SQL_LAB ROLE - Users who can run SQL queries only
    -- ========================================================================
    IF sql_lab_role_id IS NOT NULL THEN
        DELETE FROM ab_permission_view_role WHERE role_id = sql_lab_role_id;
        
        INSERT INTO ab_permission_view_role (permission_view_id, role_id)
        SELECT DISTINCT pv.id, sql_lab_role_id
        FROM ab_permission_view pv
        INNER JOIN ab_permission p ON pv.permission_id = p.id
        INNER JOIN ab_view_menu vm ON pv.view_menu_id = vm.id
        WHERE vm.name IN ('Database', 'Dataset', 'SQLLab', 'Api', 'Superset', 'MenuApi', 
                          'DynamicPlugin', 'Databases', 'Data', 'SavedQuery')
        AND p.name IN ('can_read', 'can_access', 'can_query', 'can_query_form_data', 
                       'can_estimate_query_cost', 'can_run_sync_queries', 'can_run_async_queries',
                       'can_execute_sql_query', 'can_show', 'can_get', 'menu_access')
        ON CONFLICT (permission_view_id, role_id) DO NOTHING;
    END IF;
    
    -- ========================================================================
    -- PUBLIC ROLE - Same as Gamma (anonymous users can explore + build charts)
    -- ========================================================================
    DELETE FROM ab_permission_view_role WHERE role_id = public_role_id;
    
    INSERT INTO ab_permission_view_role (permission_view_id, role_id)
    SELECT DISTINCT pv.id, public_role_id
    FROM ab_permission_view pv
    INNER JOIN ab_permission p ON pv.permission_id = p.id
    INNER JOIN ab_view_menu vm ON pv.view_menu_id = vm.id
    WHERE (vm.name IN ('Chart', 'Dashboard', 'Explore', 'Api', 'SQLLab', 'Superset', 'MenuApi', 
                       'DynamicPlugin', 'AvailableDomains', 'Tag', 'Datasets', 'Databases', 
                       'Dashboards', 'Charts', 'Data', 'ExploreFormDataRestApi', 'ExplorePermalinkRestApi'))
    AND (p.name IN ('can_read', 'can_write', 'can_query', 'can_query_form_data', 'can_estimate_query_cost',
                    'menu_access', 'can_show', 'can_get', 'can_run_async_queries', 'can_execute_sql_query',
                    'can_access'))
    ON CONFLICT (permission_view_id, role_id) DO NOTHING;
    
    RAISE NOTICE 'Role permissions configured successfully!';
END $$;

-- ============================================================================
-- VERIFICATION - Show all roles with their permission counts
-- ============================================================================
SELECT 
    r.id,
    r.name as role,
    COUNT(DISTINCT pv.id) as permission_count
FROM ab_role r
LEFT JOIN ab_permission_view_role pvr ON r.id = pvr.role_id
LEFT JOIN ab_permission_view pv ON pvr.permission_view_id = pv.id
WHERE r.name IN ('Admin', 'Alpha', 'Gamma', 'sql_lab', 'Public')
GROUP BY r.id, r.name
ORDER BY r.name;