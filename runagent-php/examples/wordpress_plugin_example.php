<?php
/**
 * Plugin Name: RunAgent WordPress Integration
 * Plugin URI: https://run-agent.ai
 * Description: Integrate RunAgent AI capabilities into your WordPress site
 * Version: 1.0.0
 * Author: RunAgent
 * Author URI: https://run-agent.ai
 * License: MIT
 * Text Domain: runagent-wp
 * 
 * This is an example WordPress plugin demonstrating how to use the RunAgent PHP SDK
 * in a WordPress environment.
 * 
 * Note: This file is designed to run within WordPress and uses WordPress functions.
 * Static analysis may show errors for undefined functions - these are expected
 * and will be available when the plugin runs in WordPress.
 */

// Exit if accessed directly
if (!defined('ABSPATH')) {
    exit;
}

// Suppress static analysis errors for WordPress functions
// @phpstan-ignore-next-line

// Include Composer autoloader
// Note: Update this path to match your WordPress installation
require_once plugin_dir_path(__FILE__) . '../vendor/autoload.php';

use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;
use RunAgent\Errors\RunAgentError;

/**
 * Main plugin class
 */
class RunAgent_WordPress_Plugin
{
    /**
     * @var RunAgent_WordPress_Plugin|null Singleton instance
     */
    private static ?RunAgent_WordPress_Plugin $instance = null;

    /**
     * Get singleton instance
     *
     * @return self
     */
    public static function getInstance(): self
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    /**
     * Constructor
     */
    private function __construct()
    {
        // Add admin menu
        add_action('admin_menu', [$this, 'addAdminMenu']);
        
        // Register settings
        add_action('admin_init', [$this, 'registerSettings']);
        
        // Add shortcode for content generation
        add_shortcode('runagent', [$this, 'runagentShortcode']);
        
        // Add AJAX endpoint
        add_action('wp_ajax_runagent_generate', [$this, 'ajaxGenerateContent']);
    }

    /**
     * Add admin menu
     */
    public function addAdminMenu(): void
    {
        add_menu_page(
            'RunAgent Settings',
            'RunAgent',
            'manage_options',
            'runagent-settings',
            [$this, 'renderSettingsPage'],
            'dashicons-admin-generic',
            80
        );
    }

    /**
     * Register plugin settings
     */
    public function registerSettings(): void
    {
        register_setting('runagent_settings', 'runagent_api_key');
        register_setting('runagent_settings', 'runagent_agent_id');
        register_setting('runagent_settings', 'runagent_entrypoint_tag');
        register_setting('runagent_settings', 'runagent_base_url');
    }

    /**
     * Render settings page
     */
    public function renderSettingsPage(): void
    {
        ?>
        <div class="wrap">
            <h1>RunAgent Settings</h1>
            <form method="post" action="options.php">
                <?php
                settings_fields('runagent_settings');
                do_settings_sections('runagent_settings');
                ?>
                <table class="form-table">
                    <tr>
                        <th scope="row">API Key</th>
                        <td>
                            <input type="password" name="runagent_api_key" 
                                   value="<?php echo esc_attr(get_option('runagent_api_key')); ?>" 
                                   class="regular-text" />
                            <p class="description">Your RunAgent API key</p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">Agent ID</th>
                        <td>
                            <input type="text" name="runagent_agent_id" 
                                   value="<?php echo esc_attr(get_option('runagent_agent_id')); ?>" 
                                   class="regular-text" />
                            <p class="description">The ID of your deployed agent</p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">Entrypoint Tag</th>
                        <td>
                            <input type="text" name="runagent_entrypoint_tag" 
                                   value="<?php echo esc_attr(get_option('runagent_entrypoint_tag', 'generic')); ?>" 
                                   class="regular-text" />
                            <p class="description">The entrypoint tag to use (default: generic)</p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">Base URL (Optional)</th>
                        <td>
                            <input type="text" name="runagent_base_url" 
                                   value="<?php echo esc_attr(get_option('runagent_base_url')); ?>" 
                                   class="regular-text" 
                                   placeholder="https://backend.run-agent.ai" />
                            <p class="description">Leave empty to use default</p>
                        </td>
                    </tr>
                </table>
                <?php submit_button(); ?>
            </form>
        </div>
        <?php
    }

    /**
     * Create RunAgent client from settings
     *
     * @return RunAgentClient
     * @throws RunAgentError
     */
    private function createClient(): RunAgentClient
    {
        $apiKey = get_option('runagent_api_key');
        $agentId = get_option('runagent_agent_id');
        $entrypointTag = get_option('runagent_entrypoint_tag', 'generic');
        $baseUrl = get_option('runagent_base_url') ?: null;

        if (empty($apiKey) || empty($agentId)) {
            throw new RunAgentError(
                'CONFIGURATION_ERROR',
                'RunAgent is not properly configured. Please check your settings.',
                'Go to RunAgent settings page and configure API key and Agent ID'
            );
        }

        $config = new RunAgentClientConfig(
            agentId: $agentId,
            entrypointTag: $entrypointTag,
            apiKey: $apiKey,
            baseUrl: $baseUrl
        );

        return RunAgentClient::create($config);
    }

    /**
     * Shortcode handler: [runagent prompt="Your prompt here"]
     *
     * @param array $atts Shortcode attributes
     * @return string Generated content or error message
     */
    public function runagentShortcode(array $atts): string
    {
        $atts = shortcode_atts([
            'prompt' => '',
            'temperature' => 0.7,
        ], $atts);

        if (empty($atts['prompt'])) {
            return '<p class="runagent-error">Error: No prompt provided</p>';
        }

        try {
            $client = $this->createClient();
            $result = $client->run([
                'prompt' => $atts['prompt'],
                'temperature' => (float) $atts['temperature'],
            ]);

            return '<div class="runagent-content">' . wp_kses_post($result) . '</div>';
            
        } catch (RunAgentError $e) {
            return '<p class="runagent-error">RunAgent Error: ' . esc_html($e->getMessage()) . '</p>';
        } catch (Exception $e) {
            return '<p class="runagent-error">Unexpected Error: ' . esc_html($e->getMessage()) . '</p>';
        }
    }

    /**
     * AJAX handler for content generation
     */
    public function ajaxGenerateContent(): void
    {
        check_ajax_referer('runagent_generate', 'nonce');

        if (!current_user_can('edit_posts')) {
            wp_send_json_error(['message' => 'Insufficient permissions']);
            return;
        }

        $prompt = sanitize_text_field($_POST['prompt'] ?? '');
        
        if (empty($prompt)) {
            wp_send_json_error(['message' => 'No prompt provided']);
            return;
        }

        try {
            $client = $this->createClient();
            $result = $client->run([
                'prompt' => $prompt,
            ]);

            wp_send_json_success([
                'content' => $result,
            ]);
            
        } catch (RunAgentError $e) {
            wp_send_json_error([
                'message' => $e->getMessage(),
                'code' => $e->getErrorCode(),
                'suggestion' => $e->getSuggestion(),
            ]);
        } catch (Exception $e) {
            wp_send_json_error([
                'message' => $e->getMessage(),
            ]);
        }
    }
}

// Initialize plugin
add_action('plugins_loaded', function() {
    RunAgent_WordPress_Plugin::getInstance();
});

/**
 * Example usage in WordPress templates:
 * 
 * // In your theme or plugin:
 * <?php
 * use RunAgent\Client\RunAgentClient;
 * use RunAgent\Types\RunAgentClientConfig;
 * 
 * $config = new RunAgentClientConfig(
 *     agentId: get_option('runagent_agent_id'),
 *     entrypointTag: 'generic',
 *     apiKey: get_option('runagent_api_key')
 * );
 * 
 * $client = RunAgentClient::create($config);
 * $result = $client->run(['prompt' => 'Generate blog post title']);
 * echo esc_html($result);
 * ?>
 * 
 * // Shortcode usage in posts/pages:
 * [runagent prompt="Write a summary of this article"]
 * 
 * // AJAX usage in JavaScript:
 * jQuery.post(ajaxurl, {
 *     action: 'runagent_generate',
 *     nonce: '<?php echo wp_create_nonce('runagent_generate'); ?>',
 *     prompt: 'Your prompt here'
 * }, function(response) {
 *     if (response.success) {
 *         console.log(response.data.content);
 *     }
 * });
 */
