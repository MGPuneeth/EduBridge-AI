import { Router, Request, Response } from 'express';
import { body, validationResult } from 'express-validator';
import User from '../models/User';
import SkillProfile from '../models/SkillProfile';

const router = Router();

// POST /api/users/sync
router.post(
  '/sync',
  [
    body('name').notEmpty().withMessage('Name is required'),
    body('email').isEmail().withMessage('Valid email is required'),
    body('oauthId').notEmpty().withMessage('OAuth ID is required'),
    body('provider').isIn(['google', 'github', 'microsoft', 'facebook', 'linkedin']).withMessage('Valid provider is required'),
  ],
  async (req: Request, res: Response): Promise<any> => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }

    try {
      const { name, email, oauthId, provider } = req.body;

      let user = await User.findOne({ email });
      let isNew = false;

      if (user) {
        user.oauthId = oauthId;
        user.provider = provider;
        await user.save();
      } else {
        user = new User({
          name,
          email,
          oauthId,
          provider,
        });
        await user.save();
        isNew = true;
      }

      const latestProfile = await SkillProfile.findOne({ userId: user._id }).sort({ assessedAt: -1 });
      const latestProfileJson = latestProfile?.toObject({ flattenMaps: true });

      return res.json({
        userId: user._id.toString(),
        isNew,
        hasSkillProfile: Boolean(latestProfileJson),
        latestProfile: latestProfileJson || null
      });
    } catch (error) {
      console.error('Error syncing user:', error);
      return res.status(500).json({ error: 'Internal server error during user sync' });
    }
  }
);

export default router;
