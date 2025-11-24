import 'package:runagent/runagent.dart';
import 'package:test/test.dart';

void main() {
  group('RunAgentClientConfig', () {
    test('create factory mirrors constructor arguments', () {
      final config = RunAgentClientConfig.create(
        agentId: 'agent-123',
        entrypointTag: 'article_create',
        local: true,
        host: '127.0.0.1',
        port: 8451,
        apiKey: 'secret',
        baseUrl: 'https://example.com',
        extraParams: {'foo': 'bar'},
        enableRegistry: false,
      );

      expect(config.agentId, 'agent-123');
      expect(config.entrypointTag, 'article_create');
      expect(config.local, isTrue);
      expect(config.host, '127.0.0.1');
      expect(config.port, 8451);
      expect(config.apiKey, 'secret');
      expect(config.baseUrl, 'https://example.com');
      expect(config.extraParams, {'foo': 'bar'});
      expect(config.enableRegistry, isFalse);
    });
  });

  group('AgentArchitecture', () {
    test('fromJson normalizes agentId and entrypoints', () {
      final architecture = AgentArchitecture.fromJson({
        'agent_id': 42,
        'entrypoints': [
          {
            'tag': 'article_create',
            'file': 'main.py',
            'description': 'Create article',
          },
          {
            'tag': 123,
            'module': 'agents.writer',
          },
        ],
      });

      expect(architecture.agentId, '42');
      expect(architecture.entrypoints, hasLength(2));
      expect(architecture.entrypoints.first.tag, 'article_create');
      expect(architecture.entrypoints.first.file, 'main.py');
      expect(architecture.entrypoints.last.tag, '123');
      expect(architecture.entrypoints.last.module, 'agents.writer');
    });
  });

  group('RunInput', () {
    test('toJson includes defaults and provided values', () {
      final runInput = RunInput(
        inputArgs: ['foo'],
        inputKwargs: {'bar': 1},
        timeoutSeconds: 120,
        asyncExecution: true,
      );

      final json = runInput.toJson();

      expect(json['entrypoint_tag'], '');
      expect(json['input_args'], ['foo']);
      expect(json['input_kwargs'], {'bar': 1});
      expect(json['timeout_seconds'], 120);
      expect(json['async_execution'], isTrue);
    });
  });
}

