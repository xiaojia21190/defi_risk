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

    mapping(address => Position[]) public userPositions;

    event PositionAdded(address indexed user, address protocol, address asset, uint256 amount);
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

    function getUserPositions(address user) external view returns (Position[] memory) {
        return userPositions[user];
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
