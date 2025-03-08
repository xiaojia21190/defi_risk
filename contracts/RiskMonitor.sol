// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

contract RiskMonitor is Ownable, Pausable {
    struct Position {
        address protocol;
        address asset;
        uint256 amount;
        uint256 leverage;
        uint256 liquidationThreshold;
    }

    struct RiskAlert {
        address user;
        address protocol;
        address asset;
        uint256 riskLevel;
        uint256 timestamp;
    }

    mapping(address => Position[]) public userPositions;
    mapping(address => RiskAlert[]) public userAlerts;

    event PositionAdded(address indexed user, address protocol, address asset, uint256 amount);
    event RiskAlertCreated(address indexed user, address protocol, address asset, uint256 riskLevel);
    event PositionUpdated(address indexed user, address protocol, address asset, uint256 newAmount);

    constructor(address initialOwner) Ownable(initialOwner) {
    }

    function addPosition(
        address protocol,
        address asset,
        uint256 amount,
        uint256 leverage,
        uint256 liquidationThreshold
    ) external {
        Position memory newPosition = Position({
            protocol: protocol,
            asset: asset,
            amount: amount,
            leverage: leverage,
            liquidationThreshold: liquidationThreshold
        });

        userPositions[msg.sender].push(newPosition);
        emit PositionAdded(msg.sender, protocol, asset, amount);
    }

    function createRiskAlert(
        address user,
        address protocol,
        address asset,
        uint256 riskLevel
    ) external onlyOwner {
        RiskAlert memory alert = RiskAlert({
            user: user,
            protocol: protocol,
            asset: asset,
            riskLevel: riskLevel,
            timestamp: block.timestamp
        });

        userAlerts[user].push(alert);
        emit RiskAlertCreated(user, protocol, asset, riskLevel);
    }

    function getUserPositions(address user) external view returns (Position[] memory) {
        return userPositions[user];
    }

    function getUserAlerts(address user) external view returns (RiskAlert[] memory) {
        return userAlerts[user];
    }

    function updatePosition(
        uint256 positionIndex,
        uint256 newAmount
    ) external {
        require(positionIndex < userPositions[msg.sender].length, "Invalid position index");

        Position storage position = userPositions[msg.sender][positionIndex];
        position.amount = newAmount;

        emit PositionUpdated(msg.sender, position.protocol, position.asset, newAmount);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }
}
