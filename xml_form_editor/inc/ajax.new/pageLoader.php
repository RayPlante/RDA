<?php
/**
 * Page loader v0.1
 * 
 * 
 * 
 * 
 */
session_start();

$_SESSION['config']['menu_desc'] = $_SESSION['config']['_ROOT_'] . '/inc/global/menu.sample.xml';

// TODO use another way to store the menus
$universe = array('admin', 'public');

$main['public'] = array('home', 'form');
$main['admin'] = array('home', 'website', 'schemas', 'users');

$sub['public']['home'] = array();
$sub['public']['form'] = array('enter_data', 'view_xml');

$sub['admin']['home'] = array();
$sub['admin']['website'] = array();
$sub['admin']['schemas'] = array('current_model', 'manage_schemas');
$sub['admin']['users'] = array();


$defaultText = '<div id="featured-wrapper"><div id="featured">
					<h1>Not yet implemented</h1>
				</div></div>';
 
if(isset($_GET['url']))
{
	// Identifying website parts
	$url = $_GET['url'];
	$menu = array();
	
	$urlParts = explode('?', $url);
	if(isset($urlParts[1])) $menu['sub'] = 	$urlParts[1];
	
	$urlParts = explode('/', $urlParts[0]);
	
	$menu['page'] = $urlParts[count($urlParts)-1];
	$menu['section'] = $urlParts[count($urlParts)-2];
	
	if($menu['section']=='admin')
	{
		if($menu['page']=='schemas')
		{
			if(!isset($menu['sub']) || $menu['sub']=='currentModel') require_once $_SESSION['config']['_ROOT_'].'/inc/skeleton/main/admin/xsd_cfg.inc.php';
			else if($menu['sub']=='manageSchemas') require_once $_SESSION['config']['_ROOT_'].'/inc/skeleton/main/admin/xsd_mgr.inc.php';
			else if($menu['sub']=='manageModules') require_once $_SESSION['config']['_ROOT_'].'/inc/skeleton/main/admin/mod_mgr.inc.php';
		}
		else
		{
			echo $defaultText.'<div id="main">';
			
			print_r($menu);
			
			echo '</div>';
		}
	}
	else
	{
		if($menu['page']=='home' || $menu['page']=='') require_once $_SESSION['config']['_ROOT_'].'/inc/skeleton/main/demo/public.home.inc.php';
		else if($menu['page']=='register')
		{
			if(!isset($menu['sub']) || $menu['sub']=='form') require_once $_SESSION['config']['_ROOT_'].'/inc/skeleton/main/public/register_form.inc.php';
			else if($menu['sub']=='xml') require_once $_SESSION['config']['_ROOT_'].'/inc/skeleton/main/demo/public.view_xml.inc.php';
		}
		else if($menu['page']=='search')
		{
			require_once $_SESSION['config']['_ROOT_'].'/inc/skeleton/main/demo/public.search.inc.php';
		}
		else
		{
			echo $defaultText.'<div id="main">';
			
			print_r($menu);
			
			echo '</div>';
		}
	}
	
	
	
	
}
?>