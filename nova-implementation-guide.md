# Nova-Activepieces Two-Layer Implementation Guide

## Frontend Implementation

```javascript
// NovaStageComponent.jsx
const NovaStageView = () => {
  const [selectedStage, setSelectedStage] = useState(null);
  const [showActivepieces, setShowActivepieces] = useState(false);

  const handleStageClick = (stageId) => {
    setSelectedStage(stageId);
    setShowActivepieces(true);
  };

  return (
    <div className="nova-workflow">
      <div className="nova-stages">
        {novaStages.map(stage => (
          <StageCard 
            key={stage.id}
            stage={stage}
            onClick={() => handleStageClick(stage.id)}
          />
        ))}
      </div>
      
      {showActivepieces && (
        <ActivepiecesPanel 
          stageId={selectedStage}
          onClose={() => setShowActivepieces(false)}
        />
      )}
    </div>
  );
};
```

## Backend API Structure

```javascript
// api/nova-workflow.js
class NovaWorkflowAPI {
  async getWorkflowStages() {
    return {
      stages: novaStages,
      connections: this.generateConnections()
    };
  }

  async getActivepiecesConfig(stageId) {
    return activepiecesConfig[stageId];
  }

  async updateActivepieceConfig(stageId, pieceId, config) {
    // Update specific activepiece configuration
    await this.validateConfig(config);
    return this.saveConfig(stageId, pieceId, config);
  }

  async executeWorkflow(invoiceData) {
    const workflow = await this.buildWorkflow();
    return this.activepiecesClient.execute(workflow, invoiceData);
  }
}
```

## Activepieces Integration

```javascript
// activepieces-integration.js
class ActivepiecesIntegration {
  constructor(apiKey, instanceUrl) {
    this.client = new ActivepiecesClient({
      apiKey,
      instanceUrl
    });
  }

  async createFlow(novaStageId, pieces) {
    const flow = {
      name: `nova-${novaStageId}`,
      trigger: this.getTriggerForStage(novaStageId),
      actions: pieces.map(piece => this.convertToAction(piece))
    };
    
    return await this.client.flows.create(flow);
  }

  convertToAction(pieceConfig) {
    return {
      name: pieceConfig.piece,
      type: pieceConfig.action,
      settings: pieceConfig.config
    };
  }
}
```

## Key Features

1. **Stage Visibility Control**
   - Nova stages are always visible
   - Activepieces stages appear on click
   - Slide-in panel for configuration

2. **Configuration Management**
   - JSON-based configuration
   - Real-time validation
   - Preview before apply

3. **Workflow Execution**
   - Sequential stage processing
   - Error handling between stages
   - Status tracking

4. **Customization Options**
   - Drag-drop piece reordering
   - Enable/disable pieces
   - Custom piece parameters

## Database Schema

```sql
-- Nova stages table
CREATE TABLE nova_stages (
  id VARCHAR(50) PRIMARY KEY,
  name VARCHAR(100),
  icon VARCHAR(50),
  position INTEGER,
  status VARCHAR(20)
);

-- Activepieces configuration
CREATE TABLE activepieces_config (
  id UUID PRIMARY KEY,
  nova_stage_id VARCHAR(50) REFERENCES nova_stages(id),
  piece_id VARCHAR(50),
  config JSONB,
  enabled BOOLEAN DEFAULT true,
  position INTEGER
);

-- Workflow execution logs
CREATE TABLE workflow_executions (
  id UUID PRIMARY KEY,
  invoice_id VARCHAR(100),
  stage_id VARCHAR(50),
  piece_id VARCHAR(50),
  status VARCHAR(20),
  error_message TEXT,
  executed_at TIMESTAMP
);
```