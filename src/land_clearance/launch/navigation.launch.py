"""Contest navigation with exactly one final /cmd_vel writer."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    share = Path(get_package_share_directory('land_clearance'))
    params = str(share / 'config/nav2.yaml')
    nodes = []
    components = [('nav2_map_server', 'map_server'), ('nav2_amcl', 'amcl'),
                  ('nav2_controller', 'controller_server'),
                  ('nav2_smoother', 'smoother_server'), ('nav2_planner', 'planner_server'),
                  ('nav2_behaviors', 'behavior_server'), ('nav2_bt_navigator', 'bt_navigator')]
    for package, executable in components:
        overrides = {'use_sim_time': True}
        if executable == 'map_server':
            overrides['yaml_filename'] = str(share / 'maps/land_shoot_map.yaml')
        nodes.append(Node(package=package, executable=executable, name=executable,
                          parameters=[params, overrides], output='screen',
                          remappings=[('cmd_vel', '/mission/nav_vel')]))
    nodes.append(Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
                      name='land_navigation_lifecycle', output='screen',
                      parameters=[{'use_sim_time': True, 'autostart': True,
                                   'node_names': [name for _, name in components]}]))
    nodes.append(Node(package='land_clearance', executable='velocity_gate', output='screen'))
    return LaunchDescription(nodes)
